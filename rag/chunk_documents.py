"""
Document Chunking — Step 2
Splits extracted page text into overlapping chunks with metadata.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))


def chunk_pages(card_name: str, pages: list[dict]) -> list[dict]:
    """
    Split a card's extracted pages into overlapping text chunks.

    Args:
        card_name: Name of the credit card
        pages: List of {page_number, text} dicts from ingest_pdfs

    Returns:
        List of chunk dicts: {card_name, chunk_text, page_number, chunk_index, metadata}
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    global_chunk_idx = 0

    for page in pages:
        page_num = page["page_number"]
        text = page["text"]

        if not text.strip():
            continue

        raw_chunks = splitter.split_text(text)

        for local_idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if len(chunk_text) < 50:   # skip tiny fragments
                continue

            all_chunks.append({
                "card_name":   card_name,
                "chunk_text":  chunk_text,
                "page_number": page_num,
                "chunk_index": global_chunk_idx,
                "metadata": {
                    "card_name":   card_name,
                    "page_number": page_num,
                    "local_chunk_index": local_idx,
                    "chunk_size":  len(chunk_text),
                },
            })
            global_chunk_idx += 1

    return all_chunks


def chunk_all_cards(ingestion_results: dict) -> dict[str, list[dict]]:
    """
    Chunk all cards' pages.

    Args:
        ingestion_results: {card_name: (card_document, pages_list)}

    Returns:
        {card_name: [chunk_dicts]}
    """
    chunked = {}
    for card_name, (card_doc, pages) in ingestion_results.items():
        chunks = chunk_pages(card_name, pages)
        chunked[card_name] = chunks
        print(f"[OK] Chunked {card_name}: {len(chunks)} chunks from {len(pages)} pages")
    return chunked
