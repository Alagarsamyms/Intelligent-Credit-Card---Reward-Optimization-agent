"""
PDF Ingestion Pipeline — Step 1
Reads credit card PDF documents, extracts text, and stores document metadata.
"""
import os
import sys
import re
from datetime import date
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
from database.db import get_db_context
from database.models import CardDocument

load_dotenv()

RAW_PDFS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_pdfs")

# Metadata for each card PDF — issuer, type, effective date
CARD_METADATA = {
    "axis_atlas.pdf": {
        "card_name": "Axis Atlas",
        "issuer": "Axis Bank",
        "document_type": "terms_and_rewards",
        "effective_date": date(2025, 1, 1),
    },
    "hdfc_diners_club_black.pdf": {
        "card_name": "HDFC Diners Club Black",
        "issuer": "HDFC Bank",
        "document_type": "terms_and_rewards",
        "effective_date": date(2025, 1, 1),
    },
    "hdfc_infinia.pdf": {
        "card_name": "HDFC Infinia",
        "issuer": "HDFC Bank",
        "document_type": "terms_and_rewards",
        "effective_date": date(2025, 1, 1),
    },
    "amex_platinum_travel.pdf": {
        "card_name": "Amex Platinum Travel",
        "issuer": "American Express",
        "document_type": "terms_and_rewards",
        "effective_date": date(2025, 1, 1),
    },
    "sbi_cashback.pdf": {
        "card_name": "SBI Cashback",
        "issuer": "State Bank of India",
        "document_type": "terms_and_rewards",
        "effective_date": date(2025, 1, 1),
    },
}


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from a PDF file page by page using PyMuPDF.
    Returns a list of dicts: {page_number, text}
    """
    pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            # Clean up whitespace while preserving structure
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            if text:
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                })
        doc.close()
    except Exception as e:
        print(f"[ERR] Error reading {pdf_path}: {e}")
    return pages


def ingest_pdf(pdf_filename: str, db) -> tuple[str, list[dict]]:
    """
    Ingest a single PDF: register its metadata in card_documents and return pages.
    Returns: (document_id_string, pages)
    """
    pdf_path = os.path.join(RAW_PDFS_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"[WARN]  File not found: {pdf_path}. Skipping.")
        return None, []

    meta = CARD_METADATA.get(pdf_filename, {})
    if not meta:
        print(f"[WARN]  No metadata defined for {pdf_filename}. Skipping.")
        return None, []

    # Check if document already exists
    existing = db.query(CardDocument).filter_by(
        card_name=meta["card_name"],
        document_type=meta["document_type"],
    ).first()

    if existing:
        print(f"[INFO]  Already ingested: {meta['card_name']} — skipping re-ingestion.")
        pages = extract_text_from_pdf(pdf_path)
        return str(existing.document_id), pages

    # Create document record
    card_doc = CardDocument(
        card_name=meta["card_name"],
        issuer=meta["issuer"],
        document_type=meta["document_type"],
        effective_date=meta.get("effective_date"),
        file_path=pdf_path,
    )
    db.add(card_doc)
    db.flush()  # get the UUID

    pages = extract_text_from_pdf(pdf_path)
    print(f"[OK] Ingested: {meta['card_name']} — {len(pages)} pages extracted.")
    return str(card_doc.document_id), pages


def ingest_all_pdfs() -> dict[str, tuple]:
    """
    Ingest all PDFs in the raw_pdfs directory.
    Returns: {card_name: (document_id, pages_list)}
    """
    results = {}
    pdf_files = [f for f in os.listdir(RAW_PDFS_DIR) if f.endswith(".pdf")]

    if not pdf_files:
        print(f"[WARN]  No PDF files found in {RAW_PDFS_DIR}")
        return results

    with get_db_context() as db:
        for pdf_file in pdf_files:
            document_id, pages = ingest_pdf(pdf_file, db)
            if document_id:
                # Find the card name from metadata since we don't have the object
                meta = CARD_METADATA.get(pdf_file, {})
                if meta:
                    results[meta["card_name"]] = (document_id, pages)

    print(f"\n[OK] Ingestion complete. {len(results)} card documents processed.")
    return results


if __name__ == "__main__":
    ingest_all_pdfs()
