"""
SQLAlchemy ORM models for all 6 database tables.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, Integer, Numeric, Boolean,
    ForeignKey, DateTime, Date, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class CardDocument(Base):
    __tablename__ = "card_documents"

    document_id   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_name     = Column(String(100), nullable=False)
    issuer        = Column(String(100), nullable=False)
    document_type = Column(String(50), nullable=False)
    effective_date = Column(Date)
    source_url    = Column(Text)
    file_path     = Column(Text)
    uploaded_at   = Column(DateTime, default=datetime.utcnow)
    is_active     = Column(Boolean, default=True)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CardDocument {self.card_name} ({self.document_type})>"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id   = Column(UUID(as_uuid=True), ForeignKey("card_documents.document_id", ondelete="CASCADE"))
    card_name     = Column(String(100), nullable=False)
    chunk_text    = Column(Text, nullable=False)
    page_number   = Column(Integer)
    chunk_index   = Column(Integer)
    embedding     = Column(Vector(1536))   # text-embedding-3-small dims
    metadata_json = Column(JSONB, default=dict)
    created_at    = Column(DateTime, default=datetime.utcnow)

    document = relationship("CardDocument", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk {self.card_name} chunk={self.chunk_index}>"


class RewardRule(Base):
    __tablename__ = "reward_rules"

    rule_id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_name        = Column(String(100), nullable=False)
    spend_category   = Column(String(100), nullable=False)
    reward_rate      = Column(Numeric(10, 4), nullable=False)
    reward_unit      = Column(String(50), nullable=False)
    reward_type      = Column(String(50), nullable=False)
    cap_type         = Column(String(30))
    cap_value        = Column(Numeric(15, 2))
    exclusion_flag   = Column(Boolean, default=False)
    exclusion_notes  = Column(Text)
    milestone_flag   = Column(Boolean, default=False)
    milestone_spend  = Column(Numeric(15, 2))
    milestone_bonus  = Column(Numeric(15, 2))
    source_chunk_id  = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id"))
    confidence_score = Column(Numeric(3, 2), default=0.9)
    effective_date   = Column(Date)
    created_at       = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RewardRule {self.card_name} | {self.spend_category} | {self.reward_rate} {self.reward_unit}>"


class TransferPartner(Base):
    __tablename__ = "transfer_partners"

    partner_id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_name            = Column(String(100), nullable=False)
    partner_name         = Column(String(100), nullable=False)
    partner_type         = Column(String(50), nullable=False)
    transfer_ratio       = Column(Numeric(5, 2), nullable=False)
    minimum_points       = Column(Integer, default=1000)
    maximum_points       = Column(Integer)
    processing_time_days = Column(Integer, default=3)
    effective_date       = Column(Date)
    source_chunk_id      = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id"))
    created_at           = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TransferPartner {self.card_name} → {self.partner_name} @ {self.transfer_ratio}>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id                = Column(String(100), primary_key=True)
    cards_owned            = Column(JSONB, default=list)
    preferred_reward_type  = Column(String(50), default="points")
    point_valuation        = Column(JSONB, default=dict)
    monthly_spend_pattern  = Column(JSONB, default=dict)
    preferred_partners     = Column(JSONB, default=list)
    conversation_summary   = Column(Text)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile {self.user_id}>"


class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"

    query_id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(String(100))
    query_text          = Column(Text, nullable=False)
    intent              = Column(String(100))
    retrieved_chunks    = Column(JSONB, default=list)
    recommended_card    = Column(String(100))
    estimated_value_inr = Column(Numeric(15, 2))
    confidence_score    = Column(Numeric(3, 2))
    final_answer        = Column(Text)
    tool_calls          = Column(JSONB, default=list)
    latency_ms          = Column(Integer)
    token_usage         = Column(JSONB, default=dict)
    guardrail_flags     = Column(JSONB, default=list)
    human_approved      = Column(Boolean)
    langsmith_run_id    = Column(String(200))
    created_at          = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RecommendationLog {self.query_id} | {self.recommended_card}>"
