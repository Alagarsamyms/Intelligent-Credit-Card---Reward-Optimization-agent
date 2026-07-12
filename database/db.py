"""
Database connection management with SQLAlchemy + pgvector.
"""
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

load_dotenv(override=True)

def _get_database_url() -> str:
    """Get DATABASE_URL from env or Streamlit secrets."""
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            import streamlit as st  # noqa: PLC0415
            url = st.secrets.get("DATABASE_URL", "")
        except Exception:
            pass
    return url or "postgresql://postgres:password@localhost:5432/credit_card_rewards"

DATABASE_URL = _get_database_url()


engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for use outside FastAPI (scripts, agents)."""
    db = SessionLocal()
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
    with engine.connect() as conn:
        conn.execute(text(schema_sql))
        conn.commit()
    print("[OK] Database initialized successfully.")


def check_connection() -> bool:
    """Quick health check for the database connection."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERR] Database connection failed: {e}")
        return False
