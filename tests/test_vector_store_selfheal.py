"""Unit test for the stale-DOI-duplicate self-heal (no network/model needed)."""

from unittest.mock import MagicMock

from qdrant_client.models import FilterSelector

from core.vector_store import VectorStore


def _conds(x):
    return list(x or [])


def test_cleanup_builds_doi_match_and_article_id_exclusion():
    # Bypass __init__ so we don't load bge-m3 / connect to Qdrant.
    vs = object.__new__(VectorStore)
    vs.client = MagicMock()
    vs.collection_name = "scientific_articles"

    vs._cleanup_stale_doi_duplicates("10.1007/978-3-031-17899-3_16", keep_article_id="KEEP-ID")

    assert vs.client.delete.called, "self-heal must issue a delete"
    sel = vs.client.delete.call_args.kwargs["points_selector"]
    assert isinstance(sel, FilterSelector)

    flt = sel.filter
    # must: doi == target  → only this paper's DOI
    must = _conds(flt.must)
    assert any(getattr(c, "key", None) == "doi" and c.match.value == "10.1007/978-3-031-17899-3_16"
               for c in must), "must filter on the target DOI"
    # must_not: article_id == keep → never delete the freshly-stored entry
    must_not = _conds(flt.must_not)
    assert any(getattr(c, "key", None) == "article_id" and c.match.value == "KEEP-ID"
               for c in must_not), "must exclude the kept article_id"


def test_cleanup_swallows_errors():
    """A self-heal failure must never break ingestion."""
    vs = object.__new__(VectorStore)
    vs.client = MagicMock()
    vs.client.delete.side_effect = RuntimeError("qdrant down")
    vs.collection_name = "scientific_articles"
    # Should not raise.
    vs._cleanup_stale_doi_duplicates("10.x/y", keep_article_id="KEEP")
