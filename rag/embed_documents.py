"""
Embedding & Storage — Step 3
Generates OpenAI embeddings for chunks and stores in PostgreSQL with pgvector.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from openai import OpenAI
from database.db import get_db_context
from database.models import DocumentChunk

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
BATCH_SIZE = 100  # OpenAI embedding API batch size


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using OpenAI API.
    Handles rate limiting with exponential backoff.
    """
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        # Clean texts — remove newlines (recommended by OpenAI)
        batch_clean = [t.replace("\n", " ").strip() for t in batch]

        for attempt in range(3):
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch_clean,
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                wait_time = 2 ** attempt
                print(f"[WARN]  Embedding API error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

    return embeddings


def embed_and_store(
    card_name: str,
    chunks: list[dict],
    document_id,
) -> int:
    """
    Embed chunks and store in document_chunks table.

    Args:
        card_name: Name of the credit card
        chunks: List of chunk dicts from chunk_documents
        document_id: UUID of the parent CardDocument record

    Returns:
        Number of chunks stored
    """
    if not chunks:
        return 0

    texts = [c["chunk_text"] for c in chunks]
    print(f"  🔄 Generating embeddings for {card_name} ({len(texts)} chunks)...")
    embeddings = embed_texts(texts)

    with get_db_context() as db:
        # Remove old chunks for this card (for re-ingestion safety)
        db.query(DocumentChunk).filter_by(card_name=card_name).delete()

        chunk_records = []
        for chunk, embedding in zip(chunks, embeddings):
            record = DocumentChunk(
                document_id=document_id,
                card_name=chunk["card_name"],
                chunk_text=chunk["chunk_text"],
                page_number=chunk.get("page_number"),
                chunk_index=chunk.get("chunk_index"),
                embedding=embedding,
                metadata_json=chunk.get("metadata", {}),
            )
            chunk_records.append(record)

        db.add_all(chunk_records)

    print(f"  [OK] Stored {len(chunk_records)} chunks for {card_name}")
    return len(chunk_records)


def embed_all_cards(ingestion_results: dict, chunked: dict) -> dict[str, int]:
    """
    Embed and store chunks for all cards.

    Args:
        ingestion_results: {card_name: (card_document, pages)}
        chunked: {card_name: [chunk_dicts]}

    Returns:
        {card_name: chunk_count}
    """
    totals = {}
    for card_name, (document_id, _) in ingestion_results.items():
        chunks = chunked.get(card_name, [])
        count = embed_and_store(card_name, chunks, document_id)
        totals[card_name] = count
    return totals
