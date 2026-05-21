from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import logging

from core.vector_store import VectorStore

# === Logging Setup ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("pede_api")

# === Initialize App & VectorStore ===
app = FastAPI(
    title="PEDE Vector Search API",
    description="Microservice for semantic search over scientific articles in Qdrant.",
    version="1.0.0",
)

# Initialize vector store at startup (loads the embedding model once into memory)
logger.info("Initializing VectorStore for API...")
try:
    vector_store = VectorStore()
except Exception as e:
    logger.error(f"Failed to initialize VectorStore: {e}")
    vector_store = None

# === Request/Response Models ===
class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    article_id: Optional[str] = None
    doi: Optional[str] = None
    section_filter: Optional[str] = None

class ChunkMetadata(BaseModel):
    article_id: str
    title: str
    authors: str
    doi: Optional[str]
    section_header: str
    content_type: str
    chunk_index: int
    total_chunks: int

class SearchResult(BaseModel):
    score: float
    content: str
    metadata: ChunkMetadata

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_found: int


# === Endpoints ===
@app.get("/")
def health_check():
    if not vector_store:
        raise HTTPException(status_code=503, detail="VectorStore not initialized")
    
    info = vector_store.get_collection_info()
    return {
        "status": "online",
        "collection": info["name"],
        "total_chunks_in_db": info["points_count"]
    }

@app.post("/search", response_model=SearchResponse)
def search_articles(req: SearchRequest):
    if not vector_store:
        raise HTTPException(status_code=503, detail="VectorStore not initialized")
    
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    logger.info(f"Received search query: '{req.query}' (limit={req.limit})")
    
    # Convert single article_id to list if provided
    article_ids = [req.article_id] if req.article_id else None
    
    # Perform semantic search
    try:
        raw_results = vector_store.search(
            query=req.query,
            n_results=req.limit,
            article_ids=article_ids,
            section_filter=req.section_filter,
            doi_filter=req.doi,
        )
        
        # Format results
        formatted_results = []
        for r in raw_results:
            meta = r["metadata"]
            formatted_results.append(
                SearchResult(
                    score=r["score"],
                    content=r["content"],
                    metadata=ChunkMetadata(
                        article_id=meta.get("article_id", ""),
                        title=meta.get("title", ""),
                        authors=meta.get("authors", ""),
                        doi=meta.get("doi"),
                        section_header=meta.get("section_header", ""),
                        content_type=meta.get("content_type", ""),
                        chunk_index=meta.get("chunk_index", 0),
                        total_chunks=meta.get("total_chunks", 0),
                    )
                )
            )
            
        return SearchResponse(
            results=formatted_results,
            total_found=len(formatted_results)
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
