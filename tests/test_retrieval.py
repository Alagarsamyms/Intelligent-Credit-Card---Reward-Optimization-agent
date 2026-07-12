"""
Retrieval Unit Tests
Tests the hybrid retrieval system (vector + keyword) with expected card coverage.

Run: pytest tests/test_retrieval.py -v

These tests mock the DB layer so no live connection is required.
For live integration tests, set RUN_LIVE_TESTS=1 in your environment.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Unit tests for retrieval utility functions (no DB needed) ─────────────────

class TestKeywordFilter:
    """Test the keyword re-ranking function in isolation."""

    def test_chunks_with_matching_keywords_ranked_higher(self):
        """Chunks containing query keywords should be ranked above those without."""
        from rag.retrieval import keyword_filter

        chunks = [
            {"chunk_id": "1", "card_name": "Card A", "chunk_text": "dining restaurant zomato", "similarity": 0.60},
            {"chunk_id": "2", "card_name": "Card B", "chunk_text": "flight travel EDGE Miles",  "similarity": 0.65},
        ]
        # Flight keyword boosts chunk 2
        result = keyword_filter(chunks, ["flight", "travel"])
        assert result[0]["chunk_id"] == "2"

    def test_no_keywords_preserves_similarity_order(self):
        """With no keywords, original similarity ranking is maintained."""
        from rag.retrieval import keyword_filter

        chunks = [
            {"chunk_id": "1", "card_name": "A", "chunk_text": "abc", "similarity": 0.80},
            {"chunk_id": "2", "card_name": "B", "chunk_text": "xyz", "similarity": 0.50},
        ]
        result = keyword_filter(chunks, [])
        assert result[0]["chunk_id"] == "1"

    def test_keyword_boost_is_additive(self):
        """Each keyword hit adds a small boost above the base similarity score."""
        from rag.retrieval import keyword_filter

        chunks = [
            {"chunk_id": "low",  "card_name": "A", "chunk_text": "flight travel airline", "similarity": 0.50},
            {"chunk_id": "high", "card_name": "B", "chunk_text": "dining restaurant",     "similarity": 0.70},
        ]
        # 'flight' and 'travel' both hit chunk 'low': boost = 2 * 0.05 = 0.10 → effective 0.60
        result = keyword_filter(chunks, ["flight", "travel"])
        assert result[0]["chunk_id"] == "high"  # 0.70 still beats 0.60


class TestCategoryKeywords:
    """Verify that retrieve_by_category maps categories to the right keywords."""

    @pytest.mark.parametrize("category,expected_kw", [
        ("flights",   "EDGE Miles"),
        ("hotels",    "hotel"),
        ("dining",    "zomato"),
        ("groceries", "bigbasket"),
        ("fuel",      "petrol"),
        ("insurance", "excluded"),
        ("rent",      "rent"),
        ("utilities", "BBPS"),
    ])
    def test_known_categories_have_relevant_keywords(self, category, expected_kw):
        """Each spend category must include at least one representative keyword."""
        from rag.retrieval import retrieve_by_category
        import rag.retrieval as retrieval_module

        # Patch retrieve to capture keywords instead of hitting DB
        captured = {}
        def mock_retrieve(query, card_filter=None, top_k=None, keywords=None):
            captured["keywords"] = keywords or []
            return []

        original = retrieval_module.retrieve
        retrieval_module.retrieve = mock_retrieve
        try:
            retrieve_by_category(category)
        finally:
            retrieval_module.retrieve = original

        assert any(expected_kw.lower() in kw.lower() for kw in captured.get("keywords", [])), (
            f"Category '{category}' keywords {captured.get('keywords')} "
            f"don't contain expected keyword '{expected_kw}'"
        )


# ── Integration tests (live DB) — skipped unless RUN_LIVE_TESTS=1 ─────────────

LIVE = os.getenv("RUN_LIVE_TESTS", "0") == "1"
skip_if_no_live = pytest.mark.skipif(not LIVE, reason="RUN_LIVE_TESTS not set")


class TestRetrievalIntegration:
    """
    End-to-end retrieval tests that require a live database.
    Enable with:   RUN_LIVE_TESTS=1 pytest tests/test_retrieval.py -v -k integration
    """

    @skip_if_no_live
    def test_flight_query_returns_axis_atlas_chunk(self):
        """A flight query must surface at least one Axis Atlas chunk."""
        from rag.retrieval import retrieve
        chunks = retrieve("I am spending Rs. 50000 on flights", top_k=5)
        assert len(chunks) > 0, "Retriever returned 0 chunks for flight query"
        card_names = [c["card_name"] for c in chunks]
        assert "Axis Atlas" in card_names, (
            f"Expected 'Axis Atlas' in results but got: {card_names}"
        )

    @skip_if_no_live
    def test_insurance_query_retrieves_exclusion_chunk(self):
        """Insurance query must return at least one chunk mentioning exclusion."""
        from rag.retrieval import retrieve
        chunks = retrieve("insurance premium payment exclusion", top_k=5)
        assert len(chunks) > 0
        texts = " ".join(c["chunk_text"].lower() for c in chunks)
        assert any(w in texts for w in ["excluded", "exclusion", "not eligible"]), (
            "No exclusion-related text found in retrieved chunks for insurance query"
        )

    @skip_if_no_live
    def test_vector_similarity_scores_are_reasonable(self):
        """All returned chunks should have similarity > threshold (0.30)."""
        from rag.retrieval import retrieve
        chunks = retrieve("best credit card for dining", top_k=5)
        for chunk in chunks:
            assert chunk["similarity"] >= 0.30, (
                f"Chunk {chunk['chunk_id']} has low similarity {chunk['similarity']:.3f}"
            )

    @skip_if_no_live
    def test_category_retrieval_flights(self):
        """retrieve_by_category('flights') must return at least one relevant chunk."""
        from rag.retrieval import retrieve_by_category
        chunks = retrieve_by_category("flights")
        assert len(chunks) > 0
        texts = " ".join(c["chunk_text"].lower() for c in chunks)
        assert any(w in texts for w in ["flight", "travel", "airline", "edge miles"])

    @skip_if_no_live
    def test_card_filter_limits_results(self):
        """card_filter parameter must restrict results to specified cards."""
        from rag.retrieval import retrieve
        chunks = retrieve("reward points", card_filter=["Axis Atlas"], top_k=5)
        for chunk in chunks:
            assert chunk["card_name"] == "Axis Atlas", (
                f"Expected only Axis Atlas but got {chunk['card_name']}"
            )

    @skip_if_no_live
    def test_rent_query_returns_exclusion(self):
        """Rent query should surface exclusion text from at least one card."""
        from rag.retrieval import retrieve_by_category
        chunks = retrieve_by_category("rent")
        assert len(chunks) > 0
        texts = " ".join(c["chunk_text"].lower() for c in chunks)
        assert any(w in texts for w in ["rent", "excluded", "not eligible", "not applicable"])

    @skip_if_no_live
    def test_hybrid_beats_vector_only_for_category(self):
        """
        Hybrid retrieval should return at least as many relevant results as
        pure vector search for a category-specific query.
        """
        from rag.retrieval import vector_search, embed_query, keyword_filter, retrieve

        query = "dining restaurant reward points"
        emb = embed_query(query)
        vector_chunks = vector_search(emb, top_k=10)
        hybrid_chunks = retrieve(query, top_k=5, keywords=["dining", "restaurant", "zomato"])

        def count_relevant(chunks):
            return sum(
                1 for c in chunks
                if any(w in c["chunk_text"].lower() for w in ["dining", "restaurant", "zomato", "food"])
            )

        vector_relevant = count_relevant(vector_chunks[:5])
        hybrid_relevant = count_relevant(hybrid_chunks)
        assert hybrid_relevant >= vector_relevant, (
            f"Hybrid ({hybrid_relevant}) should be >= vector-only ({vector_relevant})"
        )
