#!/usr/bin/env python3
"""Benchmark script for Word2Vec embedding in PEDE.

This script measures indexing and retrieval efficiency across multiple
chunk_size / chunk_overlap configurations using Word2Vec embeddings.

Usage:
    python scripts/benchmark_word2vec.py --source-dir ./data/markdown \
        --query-file ./benchmark_queries.json --output ./benchmark_word2vec_results.md

Query file format (JSON array):
[
  {
    "query": "Apa kontribusi utama paper ini?",
    "expected_article_id": "<article_id>",
    "expected_doi": "10.1234/example.doi",
    "expected_chunk_ids": ["<chunk_id1>", "<chunk_id2>"]
  }
]

If no query file is provided, the script will still benchmark indexing and
report retrieval latency for an empty query set.
"""

import argparse
import json
import logging
import math
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from core.chunker import chunk_markdown
from core.metadata_extractor import ArticleMetadata
from core.vector_store import VectorStore

try:
    import psutil
except ImportError:
    psutil = None


logger = logging.getLogger("benchmark_word2vec")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


DEFAULT_COMBINATIONS = [
    (256, 0),
    (256, 50),
    (256, 100),
    (512, 0),
    (512, 50),
    (512, 100),
    (768, 0),
    (768, 50),
    (768, 100),
    (1024, 100),
]

WORD2VEC_MODEL = "word2vec-google-news-300"
TOP_K = 5


@dataclass
class QueryItem:
    query: str
    expected_article_id: str | None = None
    expected_doi: str | None = None
    expected_chunk_ids: list[str] | None = None


@dataclass
class BenchmarkResult:
    chunk_size: int
    chunk_overlap: int
    indexing_time_s: float
    retrieval_time_ms: float
    memory_delta_mb: float
    average_similarity: float
    recall: float | None
    precision: float | None
    num_documents: int
    num_chunks: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Word2Vec embedding for PEDE")
    parser.add_argument("--source-dir", required=True, help="Directory containing markdown or PDF source files")
    parser.add_argument("--query-file", required=False, help="JSON file containing benchmark queries and expected ground truth")
    parser.add_argument("--output", default="benchmark_word2vec_results.md", help="Output markdown summary path")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Top-K search limit")
    parser.add_argument("--dry-run", action="store_true", help="Do not write results file")
    return parser.parse_args()


def load_queries(query_file: str) -> list[QueryItem]:
    if not query_file:
        return []

    with open(query_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    queries: list[QueryItem] = []
    for entry in raw:
        queries.append(
            QueryItem(
                query=entry.get("query", "").strip(),
                expected_article_id=entry.get("expected_article_id"),
                expected_doi=entry.get("expected_doi"),
                expected_chunk_ids=entry.get("expected_chunk_ids"),
            )
        )
    return queries


def discover_source_files(source_dir: str) -> list[Path]:
    source_path = Path(source_dir)
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    files = list(source_path.rglob("*.md")) + list(source_path.rglob("*.pdf"))
    if not files:
        raise FileNotFoundError(f"No .md or .pdf files found in {source_dir}")
    return sorted(files)


def load_document_text(path: Path) -> str:
    if path.suffix.lower() == ".md":
        return path.read_text(encoding="utf-8")

    from core.pdf_converter import convert_pdf_to_markdown
    return convert_pdf_to_markdown(str(path), image_dir="./data/images", write_images=False)


def build_article_metadata(path: Path) -> ArticleMetadata:
    return ArticleMetadata(
        filename=path.name,
        title=path.stem,
        authors=[],
        doi=None,
    )


class MemoryMeter:
    def __enter__(self) -> float:
        if psutil:
            self.process = psutil.Process()
            self.start = self.process.memory_info().rss
            return self.start
        tracemalloc.start()
        self.start, _ = tracemalloc.get_traced_memory()
        return float(self.start)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if psutil:
            self.end = self.process.memory_info().rss
        else:
            self.end, self.peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

    def delta_mb(self) -> float:
        if psutil:
            return float(self.end - self.start) / 1024**2
        return float(self.peak - self.start) / 1024**2


def evaluate_results(results: list[dict], query: QueryItem, top_k: int) -> tuple[float, float]:
    if not results or not query:
        return 0.0, 0.0

    expected_ids = set()
    if query.expected_article_id:
        expected_ids.add(query.expected_article_id)
    if query.expected_doi:
        expected_ids.add(query.expected_doi)
    if query.expected_chunk_ids:
        expected_ids.update(query.expected_chunk_ids)

    if not expected_ids:
        return 0.0, 0.0

    found = 0
    for point in results:
        meta = point["metadata"]
        if query.expected_chunk_ids and meta.get("chunk_id") in query.expected_chunk_ids:
            found += 1
            continue
        if query.expected_article_id and meta.get("article_id") == query.expected_article_id:
            found += 1
            continue
        if query.expected_doi and meta.get("doi") == query.expected_doi:
            found += 1
            continue

    recall = min(found / len(expected_ids), 1.0)
    precision = found / top_k
    return recall, precision


def benchmark_configuration(
    files: list[Path],
    queries: list[QueryItem],
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
) -> BenchmarkResult:
    collection_name = f"benchmark_word2vec_{chunk_size}_{chunk_overlap}"
    vector_store = VectorStore(
        embedding_model=WORD2VEC_MODEL,
        collection_name=collection_name,
    )
    vector_store.ensure_collection()

    logger.info("Starting benchmark for chunk_size=%s, chunk_overlap=%s", chunk_size, chunk_overlap)

    num_chunks = 0
    memory_meter = MemoryMeter()
    indexing_start = time.perf_counter()
    with memory_meter:
        for path in files:
            text = load_document_text(path)
            article_meta = build_article_metadata(path)
            chunks = chunk_markdown(
                text,
                article_meta,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            num_chunks += len(chunks)
            vector_store.add_chunks(chunks)
    indexing_end = time.perf_counter()
    indexing_time = indexing_end - indexing_start
    indexing_memory_mb = memory_meter.delta_mb()

    retrieval_times = []
    similarities = []
    recalls = []
    precisions = []

    if queries:
        for query in queries:
            search_start = time.perf_counter()
            results = vector_store.search(
                query=query.query,
                n_results=top_k,
            )
            search_end = time.perf_counter()
            retrieval_times.append((search_end - search_start) * 1000.0)
            similarities.extend([r["score"] for r in results if isinstance(r.get("score"), (int, float))])
            recall, precision = evaluate_results(results, query, top_k)
            recalls.append(recall)
            precisions.append(precision)
    else:
        logger.warning("No queries provided; retrieval metrics will remain empty.")

    avg_retrieval_time = mean(retrieval_times) if retrieval_times else 0.0
    avg_similarity = mean(similarities) if similarities else 0.0
    avg_recall = mean(recalls) if recalls else None
    avg_precision = mean(precisions) if precisions else None

    return BenchmarkResult(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        indexing_time_s=indexing_time,
        retrieval_time_ms=avg_retrieval_time,
        memory_delta_mb=indexing_memory_mb,
        average_similarity=avg_similarity,
        recall=avg_recall,
        precision=avg_precision,
        num_documents=len(files),
        num_chunks=num_chunks,
    )


def render_markdown(results: list[BenchmarkResult], output_path: Path | None = None) -> str:
    lines = [
        "# Word2Vec Benchmark Results",
        "",
        "| Chunk Size | Overlap | Documents | Chunks | Indexing Time (s) | Retrieval Time (ms) | Memory Delta (MB) | Similarity | Recall | Precision |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for result in results:
        lines.append(
            "| {} | {} | {} | {} | {:.2f} | {:.2f} | {:.1f} | {:.4f} | {} | {} |".format(
                result.chunk_size,
                result.chunk_overlap,
                result.num_documents,
                result.num_chunks,
                result.indexing_time_s,
                result.retrieval_time_ms,
                result.memory_delta_mb,
                result.average_similarity,
                f"{result.recall:.3f}" if result.recall is not None else "N/A",
                f"{result.precision:.3f}" if result.precision is not None else "N/A",
            )
        )

    markdown = "\n".join(lines)
    if output_path:
        output_path.write_text(markdown, encoding="utf-8")
        logger.info("Benchmark summary written to %s", output_path)
    return markdown


def main() -> None:
    args = parse_args()
    files = discover_source_files(args.source_dir)
    queries = load_queries(args.query_file) if args.query_file else []

    results: list[BenchmarkResult] = []
    for chunk_size, chunk_overlap in DEFAULT_COMBINATIONS:
        result = benchmark_configuration(
            files=files,
            queries=queries,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=args.top_k,
        )
        results.append(result)

    markdown = render_markdown(results, Path(args.output) if not args.dry_run else None)
    print(markdown)


if __name__ == "__main__":
    main()
