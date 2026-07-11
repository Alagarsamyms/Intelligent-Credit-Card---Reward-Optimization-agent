-- ============================================================
-- Credit Card Rewards Optimization Agent — Database Schema
-- ============================================================
-- Run: psql -U postgres -d credit_card_rewards -f schema.sql
-- ============================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Table 1: card_documents
-- Stores metadata about uploaded card documents
-- ============================================================
CREATE TABLE IF NOT EXISTS card_documents (
    document_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_name       VARCHAR(100) NOT NULL,
    issuer          VARCHAR(100) NOT NULL,
    document_type   VARCHAR(50)  NOT NULL,   -- 'terms', 'reward_chart', 'transfer_partner', 'exclusion'
    effective_date  DATE,
    source_url      TEXT,
    file_path       TEXT,
    uploaded_at     TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- Table 2: document_chunks
-- Stores RAG chunks with vector embeddings
-- ============================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID REFERENCES card_documents(document_id) ON DELETE CASCADE,
    card_name       VARCHAR(100) NOT NULL,
    chunk_text      TEXT NOT NULL,
    page_number     INTEGER,
    chunk_index     INTEGER,
    embedding       vector(1536),            -- OpenAI text-embedding-3-small = 1536 dims
    metadata_json   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for filtering by card name
CREATE INDEX IF NOT EXISTS idx_document_chunks_card_name
    ON document_chunks (card_name);

-- ============================================================
-- Table 3: reward_rules
-- Stores structured, extracted reward rules for calculations
-- ============================================================
CREATE TABLE IF NOT EXISTS reward_rules (
    rule_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_name           VARCHAR(100) NOT NULL,
    spend_category      VARCHAR(100) NOT NULL,   -- 'flights', 'hotels', 'dining', 'groceries', etc.
    reward_rate         NUMERIC(10, 4) NOT NULL, -- e.g., 5.0 = 5 points per unit
    reward_unit         VARCHAR(50) NOT NULL,    -- 'points_per_100_inr', 'cashback_pct', 'miles_per_100_inr'
    reward_type         VARCHAR(50) NOT NULL,    -- 'points', 'cashback', 'miles', 'vouchers'
    cap_type            VARCHAR(30),             -- 'monthly', 'quarterly', 'annual', NULL
    cap_value           NUMERIC(15, 2),          -- max points/cashback in cap period
    exclusion_flag      BOOLEAN DEFAULT FALSE,
    exclusion_notes     TEXT,
    milestone_flag      BOOLEAN DEFAULT FALSE,
    milestone_spend     NUMERIC(15, 2),          -- spend threshold for milestone
    milestone_bonus     NUMERIC(15, 2),          -- bonus points/cashback at milestone
    source_chunk_id     UUID REFERENCES document_chunks(chunk_id),
    confidence_score    NUMERIC(3, 2) DEFAULT 0.9,  -- 0.0 to 1.0
    effective_date      DATE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reward_rules_card_category
    ON reward_rules (card_name, spend_category);

-- ============================================================
-- Table 4: transfer_partners
-- Stores point transfer rules and partner ratios
-- ============================================================
CREATE TABLE IF NOT EXISTS transfer_partners (
    partner_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_name           VARCHAR(100) NOT NULL,
    partner_name        VARCHAR(100) NOT NULL,
    partner_type        VARCHAR(50) NOT NULL,  -- 'airline', 'hotel', 'other'
    transfer_ratio      NUMERIC(5, 2) NOT NULL, -- e.g., 2:1 stored as 0.5 (partner units per source point)
    minimum_points      INTEGER DEFAULT 1000,
    maximum_points      INTEGER,
    processing_time_days INTEGER DEFAULT 3,
    effective_date      DATE,
    source_chunk_id     UUID REFERENCES document_chunks(chunk_id),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transfer_partners_card
    ON transfer_partners (card_name);

-- ============================================================
-- Table 5: user_profiles
-- Stores user preferences and spend patterns
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id                 VARCHAR(100) PRIMARY KEY,
    cards_owned             JSONB DEFAULT '[]',       -- ["Axis Atlas", "HDFC DCB"]
    preferred_reward_type   VARCHAR(50) DEFAULT 'points', -- 'points', 'cashback', 'miles', 'hotel'
    point_valuation         JSONB DEFAULT '{}',       -- {"Axis Atlas": 1.0, "HDFC DCB": 0.8}
    monthly_spend_pattern   JSONB DEFAULT '{}',       -- {"flights": 40000, "dining": 30000}
    preferred_partners      JSONB DEFAULT '[]',       -- ["Air India", "Marriott"]
    conversation_summary    TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Table 6: recommendation_logs
-- Full audit trail for monitoring and evaluation
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendation_logs (
    query_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             VARCHAR(100),
    query_text          TEXT NOT NULL,
    intent              VARCHAR(100),
    retrieved_chunks    JSONB DEFAULT '[]',
    recommended_card    VARCHAR(100),
    estimated_value_inr NUMERIC(15, 2),
    confidence_score    NUMERIC(3, 2),
    final_answer        TEXT,
    tool_calls          JSONB DEFAULT '[]',
    latency_ms          INTEGER,
    token_usage         JSONB DEFAULT '{}',
    guardrail_flags     JSONB DEFAULT '[]',
    human_approved      BOOLEAN,
    langsmith_run_id    VARCHAR(200),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_logs_user
    ON recommendation_logs (user_id, created_at DESC);
