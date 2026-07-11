"""
Retrieval — Step 4
Hybrid retrieval combining pgvector similarity search + keyword filtering.
Returns the most relevant card rule chunks for a given query.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import text, func
from database.db import get_db_context
from database.models import DocumentChunk

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 5))
SCORE_THRESHOLD = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", 0.7))


def embed_query(query: str) -> list[float]:
    """Embed a user query using OpenAI."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query.replace("\n", " ").strip(),
    )
    return response.data[0].embedding


def vector_search(
    query_embedding: list[float],
    card_filter: list[str] | None = None,
    top_k: int = TOP_K,
) -> list[dict]:
    """
    Perform cosine similarity search against document_chunks using pgvector.

    Args:
        query_embedding: Query embedding vector
        card_filter: Optional list of card names to filter by
        top_k: Number of top results to return

    Returns:
        List of chunk dicts with similarity scores
    """
    with get_db_context() as db:
        # Build pgvector cosine similarity query
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        if card_filter:
            results = db.execute(text("""
                SELECT
                    chunk_id,
                    card_name,
                    chunk_text,
                    page_number,
                    chunk_index,
                    metadata_json,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunks
                WHERE card_name = ANY(:cards)
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """), {
                "embedding": embedding_str,
                "cards": card_filter,
                "top_k": top_k,
            })
        else:
            results = db.execute(text("""
                SELECT
                    chunk_id,
                    card_name,
                    chunk_text,
                    page_number,
                    chunk_index,
                    metadata_json,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunks
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """), {
                "embedding": embedding_str,
                "top_k": top_k,
            })

        rows = results.fetchall()
        return [
            {
                "chunk_id":    str(row.chunk_id),
                "card_name":   row.card_name,
                "chunk_text":  row.chunk_text,
                "page_number": row.page_number,
                "similarity":  float(row.similarity),
                "metadata":    row.metadata_json or {},
            }
            for row in rows
            if float(row.similarity) >= SCORE_THRESHOLD
        ]


def keyword_filter(chunks: list[dict], keywords: list[str]) -> list[dict]:
    """
    Re-rank or boost chunks that contain important keywords.
    Used for hybrid retrieval.
    """
    def score_chunk(chunk):
        text_lower = chunk["chunk_text"].lower()
        keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        return chunk["similarity"] + (keyword_hits * 0.05)  # small keyword boost

    return sorted(chunks, key=score_chunk, reverse=True)


def retrieve(
    query: str,
    card_filter: list[str] | None = None,
    top_k: int = TOP_K,
    keywords: list[str] | None = None,
) -> list[dict]:
    """
    Main retrieval function — hybrid vector + keyword.

    Args:
        query: User's natural language query
        card_filter: Optional list of card names to restrict search
        top_k: Number of results to return
        keywords: Optional keywords to boost in re-ranking

    Returns:
        Ranked list of relevant chunk dicts
    """
    query_embedding = embed_query(query)

    # Vector similarity search
    chunks = vector_search(query_embedding, card_filter=card_filter, top_k=top_k * 2)

    # Keyword re-ranking if provided
    if keywords:
        chunks = keyword_filter(chunks, keywords)

    # Deduplicate by chunk_id and return top_k
    seen = set()
    deduped = []
    for chunk in chunks:
        if chunk["chunk_id"] not in seen:
            seen.add(chunk["chunk_id"])
            deduped.append(chunk)
        if len(deduped) >= top_k:
            break

    return deduped


def retrieve_by_category(category: str, card_filter: list[str] | None = None) -> list[dict]:
    """
    Convenience function to retrieve rules for a specific spend category.
    Augments query with category-specific keywords.
    """
    category_keywords = {
        "flights":    ["flight", "travel", "airline", "flying", "EDGE Miles", "accelerated"],
        "hotels":     ["hotel", "accommodation", "stay", "property", "resort"],
        "dining":     ["dining", "restaurant", "food", "swiggy", "zomato"],
        "groceries":  ["grocery", "supermarket", "fresh", "bigbasket"],
        "fuel":       ["fuel", "petrol", "surcharge waiver", "petroleum"],
        "insurance":  ["insurance", "premium", "excluded", "not eligible"],
        "rent":       ["rent", "rental", "house", "not eligible for rewards"],
        "utilities":  ["utility", "electricity", "water", "telephone", "BBPS"],
    }

    keywords = category_keywords.get(category.lower(), [category])
    query = f"reward points or cashback for {category} spend transactions"
    return retrieve(query, card_filter=card_filter, keywords=keywords)
