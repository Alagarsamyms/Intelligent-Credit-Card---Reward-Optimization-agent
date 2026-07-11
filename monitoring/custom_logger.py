"""
Custom PostgreSQL Logger
Logs all agent interactions to the recommendation_logs table for monitoring and evaluation.
"""
import os
import sys
import time
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from database.db import get_db_context
from database.models import RecommendationLog

load_dotenv()


def log_recommendation(
    user_id: str,
    query_text: str,
    intent: str,
    retrieved_chunks: list[dict],
    recommended_card: str | None,
    estimated_value_inr: float | None,
    confidence_score: float,
    final_answer: str,
    tool_calls: list[dict],
    latency_ms: int,
    token_usage: dict,
    guardrail_flags: list[str],
    human_approved: bool | None = None,
    langsmith_run_id: str | None = None,
) -> str:
    """
    Log a complete agent interaction to the recommendation_logs table.

    Returns:
        query_id (UUID string)
    """
    # Confidence string → numeric
    confidence_map = {"HIGH": 0.95, "MEDIUM-HIGH": 0.80, "MEDIUM": 0.65, "LOW": 0.40}
    conf_numeric = confidence_map.get(str(confidence_score).upper(), 0.65)

    # Truncate chunks for storage (keep only chunk_id, card_name, similarity)
    stored_chunks = [
        {
            "chunk_id": c.get("chunk_id"),
            "card_name": c.get("card_name"),
            "similarity": round(c.get("similarity", 0), 3),
            "page": c.get("page_number"),
        }
        for c in retrieved_chunks[:10]
    ]

    try:
        with get_db_context() as db:
            log_entry = RecommendationLog(
                user_id=user_id,
                query_text=query_text[:2000],  # truncate very long queries
                intent=intent,
                retrieved_chunks=stored_chunks,
                recommended_card=recommended_card,
                estimated_value_inr=estimated_value_inr,
                confidence_score=conf_numeric,
                final_answer=final_answer[:5000],
                tool_calls=tool_calls,
                latency_ms=latency_ms,
                token_usage=token_usage,
                guardrail_flags=guardrail_flags,
                human_approved=human_approved,
                langsmith_run_id=langsmith_run_id,
            )
            db.add(log_entry)
            db.flush()
            query_id = str(log_entry.query_id)

        return query_id

    except Exception as e:
        print(f"[WARN]  Failed to log recommendation: {e}")
        return str(uuid.uuid4())


def get_recent_logs(user_id: str | None = None, limit: int = 20) -> list[dict]:
    """
    Retrieve recent recommendation logs for monitoring dashboard.

    Args:
        user_id: Optional filter by user
        limit: Number of records to retrieve

    Returns:
        List of log dicts
    """
    try:
        with get_db_context() as db:
            query = db.query(RecommendationLog).order_by(
                RecommendationLog.created_at.desc()
            )
            if user_id:
                query = query.filter_by(user_id=user_id)
            logs = query.limit(limit).all()

            return [
                {
                    "query_id": str(l.query_id),
                    "user_id": l.user_id,
                    "query_text": l.query_text,
                    "intent": l.intent,
                    "recommended_card": l.recommended_card,
                    "estimated_value_inr": float(l.estimated_value_inr) if l.estimated_value_inr else None,
                    "confidence_score": float(l.confidence_score) if l.confidence_score else None,
                    "latency_ms": l.latency_ms,
                    "token_usage": l.token_usage,
                    "guardrail_flags": l.guardrail_flags,
                    "human_approved": l.human_approved,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                    "langsmith_run_id": l.langsmith_run_id,
                }
                for l in logs
            ]
    except Exception as e:
        print(f"[WARN]  Failed to retrieve logs: {e}")
        return []


def get_monitoring_stats() -> dict:
    """
    Compute aggregate monitoring statistics for the dashboard.
    """
    try:
        with get_db_context() as db:
            from sqlalchemy import func
            total = db.query(func.count(RecommendationLog.query_id)).scalar()
            avg_latency = db.query(func.avg(RecommendationLog.latency_ms)).scalar()
            avg_confidence = db.query(func.avg(RecommendationLog.confidence_score)).scalar()
            hallucination_count = db.query(
                func.count(RecommendationLog.query_id)
            ).filter(
                RecommendationLog.guardrail_flags.op('@>')(
                    '["NO_RETRIEVED_EVIDENCE"]'
                )
            ).scalar()

        return {
            "total_queries": total or 0,
            "avg_latency_ms": round(float(avg_latency), 0) if avg_latency else 0,
            "avg_confidence": round(float(avg_confidence), 3) if avg_confidence else 0,
            "guardrail_violations": hallucination_count or 0,
        }
    except Exception as e:
        print(f"[WARN]  Failed to compute stats: {e}")
        return {"total_queries": 0, "avg_latency_ms": 0, "avg_confidence": 0, "guardrail_violations": 0}
