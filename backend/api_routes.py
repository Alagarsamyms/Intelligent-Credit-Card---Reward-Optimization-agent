"""
FastAPI Routes
"""
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from agents.graph import run_agent
from database.db import get_db
from database.models import UserProfile
from monitoring.custom_logger import log_recommendation, get_recent_logs, get_monitoring_stats
from rag.ingest_pdfs import ingest_all_pdfs
from rag.chunk_documents import chunk_all_cards
from rag.embed_documents import embed_all_cards

router = APIRouter()


# ── Pydantic Request/Response Models ─────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    thread_id: Optional[str] = None


class ApprovalRequest(BaseModel):
    thread_id: str
    user_id: str
    approved: bool
    query: str


class ProfileUpdate(BaseModel):
    cards_owned: Optional[list[str]] = None
    preferred_reward_type: Optional[str] = None
    point_valuation: Optional[dict] = None
    monthly_spend_pattern: Optional[dict] = None
    preferred_partners: Optional[list[str]] = None


class QueryResponse(BaseModel):
    query_id: Optional[str]
    final_answer: str
    recommended_card: Optional[str]
    estimated_value_inr: Optional[float]
    confidence: str
    awaiting_approval: bool
    approval_context: Optional[str]
    latency_ms: int
    token_usage: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def submit_query(req: QueryRequest, db=Depends(get_db)):
    """Submit a user query to the agent."""
    start = time.time()

    # Load user profile from DB
    profile = db.query(UserProfile).filter_by(user_id=req.user_id).first()
    user_profile = {}
    if profile:
        user_profile = {
            "cards_owned": profile.cards_owned or [],
            "preferred_reward_type": profile.preferred_reward_type,
            "point_valuation": profile.point_valuation or {},
            "monthly_spend_pattern": profile.monthly_spend_pattern or {},
            "preferred_partners": profile.preferred_partners or [],
        }

    result = run_agent(
        query=req.query,
        user_id=req.user_id,
        thread_id=req.thread_id,
        user_profile=user_profile,
    )

    latency_ms = int((time.time() - start) * 1000)

    # Log to DB
    query_id = log_recommendation(
        user_id=req.user_id,
        query_text=req.query,
        intent=result.get("intent", "unknown"),
        retrieved_chunks=result.get("retrieved_chunks", []),
        recommended_card=result.get("recommended_card"),
        estimated_value_inr=result.get("estimated_value_inr"),
        confidence_score=result.get("confidence", "MEDIUM"),
        final_answer=result.get("final_answer", ""),
        tool_calls=[],
        latency_ms=latency_ms,
        token_usage=result.get("token_usage", {}),
        guardrail_flags=result.get("guardrail_flags", []),
        human_approved=result.get("human_approved"),
        langsmith_run_id=result.get("langsmith_run_id"),
    )

    return QueryResponse(
        query_id=query_id,
        final_answer=result.get("final_answer", ""),
        recommended_card=result.get("recommended_card"),
        estimated_value_inr=result.get("estimated_value_inr"),
        confidence=result.get("confidence", "MEDIUM"),
        awaiting_approval=result.get("awaiting_approval", False),
        approval_context=result.get("approval_context"),
        latency_ms=latency_ms,
        token_usage=result.get("token_usage", {}),
    )


@router.post("/approve")
async def submit_approval(req: ApprovalRequest):
    """Submit human approval decision for transfer queries."""
    result = run_agent(
        query=req.query,
        user_id=req.user_id,
        thread_id=req.thread_id,
        human_approved=req.approved,
    )
    return {
        "final_answer": result.get("final_answer", ""),
        "approved": req.approved,
    }


@router.get("/profile/{user_id}")
async def get_profile(user_id: str, db=Depends(get_db)):
    """Get user profile."""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    return {
        "user_id": profile.user_id,
        "cards_owned": profile.cards_owned,
        "preferred_reward_type": profile.preferred_reward_type,
        "point_valuation": profile.point_valuation,
        "monthly_spend_pattern": profile.monthly_spend_pattern,
        "preferred_partners": profile.preferred_partners,
    }


@router.post("/profile/{user_id}")
async def upsert_profile(user_id: str, update: ProfileUpdate, db=Depends(get_db)):
    """Create or update user profile."""
    profile = db.query(UserProfile).filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    if update.cards_owned is not None:
        profile.cards_owned = update.cards_owned
    if update.preferred_reward_type:
        profile.preferred_reward_type = update.preferred_reward_type
    if update.point_valuation:
        profile.point_valuation = update.point_valuation
    if update.monthly_spend_pattern:
        profile.monthly_spend_pattern = update.monthly_spend_pattern
    if update.preferred_partners:
        profile.preferred_partners = update.preferred_partners

    db.commit()
    return {"status": "success", "user_id": user_id}


@router.post("/ingest")
async def trigger_ingestion():
    """Trigger the PDF ingestion pipeline."""
    try:
        ingestion_results = ingest_all_pdfs()
        chunked = chunk_all_cards(ingestion_results)
        totals = embed_all_cards(ingestion_results, chunked)
        return {
            "status": "success",
            "cards_processed": list(totals.keys()),
            "total_chunks": sum(totals.values()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/stats")
async def monitoring_stats():
    """Get aggregate monitoring statistics."""
    return get_monitoring_stats()


@router.get("/monitoring/logs")
async def monitoring_logs(user_id: Optional[str] = None, limit: int = 20):
    """Get recent recommendation logs."""
    return get_recent_logs(user_id=user_id, limit=limit)
