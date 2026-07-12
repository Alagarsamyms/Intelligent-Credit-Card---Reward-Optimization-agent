"""
Database connection management with SQLAlchemy + pgvector.
Engine is created lazily on first use so that Streamlit secrets are
available before the connection is established.
"""
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

load_dotenv(override=True)

# ── Lazy engine singleton ──────────────────────────────────────────────────────
_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    """
    Resolve DATABASE_URL at call time (not import time) so Streamlit secrets
    are available.
    """
    url = None

    # Try Streamlit secrets first (source of truth on Cloud)
    try:
        import streamlit as st  # noqa: PLC0415
        url = st.secrets.get("DATABASE_URL")
    except Exception:
        pass

    # Fallback to local environment (.env)
    if not url:
        url = os.getenv("DATABASE_URL")
    
    url = url or "postgresql://postgres:password@localhost:5432/credit_card_rewards"

    # Transparently upgrade URL scheme for psycopg3
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    return url


def _get_engine():
    """Return the shared engine + session factory, creating them on first call."""
    global _engine, _SessionLocal
    if _engine is None:
        db_url = _get_database_url()
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal


def get_db() -> Session:
    """FastAPI dependency: yields a database session."""
    _, session_factory = _get_engine()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for use outside FastAPI (scripts, agents)."""
    _, session_factory = _get_engine()
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize the database — run schema.sql."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    engine, _ = _get_engine()
    with engine.connect() as conn:
        conn.execute(text(schema_sql))
        conn.commit()
    print("[OK] Database initialized successfully.")


def check_connection() -> bool:
    """Quick health check for the database connection."""
    try:
        engine, _ = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERR] Database connection failed: {e}")
        return False
