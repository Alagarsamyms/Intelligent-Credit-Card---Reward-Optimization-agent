"""
Full pipeline setup script — run this once to initialize the project.
Usage: python setup_pipeline.py

Steps:
1. Initialize database (requires PostgreSQL + .env)
2. Generate synthetic card PDFs
3. Run PDF ingestion + chunking + embedding
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def step_1_init_db():
    print("\n" + "="*60)
    print("STEP 1: Database Initialization")
    print("="*60)
    try:
        from database.db import init_db, check_connection
        if not check_connection():
            print("[ERR] Cannot connect to database. Check DATABASE_URL in .env")
            return False
        init_db()
        return True
    except Exception as e:
        print(f"[ERR] DB initialization failed: {e}")
        return False


def step_2_generate_pdfs():
    print("\n" + "="*60)
    print("STEP 2: Generating Synthetic Card PDFs")
    print("="*60)
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "data/generate_synthetic_cards.py"],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"[ERR] PDF generation failed:\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"[ERR] PDF generation failed: {e}")
        return False


def step_3_run_pipeline():
    print("\n" + "="*60)
    print("STEP 3: Ingestion + Chunking + Embedding")
    print("="*60)
    try:
        from rag.ingest_pdfs import ingest_all_pdfs
        from rag.chunk_documents import chunk_all_cards
        from rag.embed_documents import embed_all_cards

        print("Ingesting PDFs...")
        ingestion_results = ingest_all_pdfs()

        print("Chunking documents...")
        chunked = chunk_all_cards(ingestion_results)

        print("Generating embeddings and storing in pgvector...")
        totals = embed_all_cards(ingestion_results, chunked)

        print(f"\n[OK] Pipeline complete!")
        for card, count in totals.items():
            print(f"  • {card}: {count} chunks embedded")
        return True
    except Exception as e:
        print(f"[ERR] Pipeline failed: {e}")
        return False


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   Credit Card Rewards Agent — Full Setup Pipeline       ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Run each step
    if not step_1_init_db():
        print("\n[WARN]  Skipping remaining steps due to DB failure.")
        print("Please set up PostgreSQL and update .env, then re-run.")
        sys.exit(1)

    if not step_2_generate_pdfs():
        print("\n[WARN]  PDF generation failed. Check reportlab installation.")
        sys.exit(1)

    if not step_3_run_pipeline():
        print("\n[WARN]  Pipeline failed. Check OpenAI API key and DB connection.")
        sys.exit(1)

    print("\n" + "="*60)
    print("[OK] ALL STEPS COMPLETE! Launch the app with:")
    print("   streamlit run app/streamlit_app.py")
    print("="*60)
