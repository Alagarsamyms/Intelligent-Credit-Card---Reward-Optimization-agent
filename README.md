# Intelligent Credit Card & Rewards Optimization Agent
### IITM Agentic AI Capstone Project

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4+-green)](https://langchain-ai.github.io/langgraph/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange)](https://openai.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL+pgvector-blue)](https://postgresql.org)

---

## Project Overview

An **agentic AI pipeline** that helps users choose the best credit card for any transaction and optimize their reward points. Unlike a basic RAG chatbot, this agent:

- **Retrieves** card rules from a pgvector database (RAG)
- **Calculates** rewards deterministically (no LLM math)
- **Compares** all eligible cards and ranks them
- **Remembers** user preferences across a conversation (LangGraph memory)
- **Guards** against hallucination — refuses to answer without retrieved evidence
- **Asks** for human approval before irreversible transfer decisions (HITL)
- **Monitors** all traces via LangSmith + PostgreSQL audit logs

---

## Architecture

```
User Query
    ↓
[1] User Input Node
    ↓
[2] Intent Classification (GPT-4o)
    ↓
[3] Clarification Node (multi-turn)
    ↓
[4] Retrieval Node (pgvector hybrid search)
    ↓
[5] Rule Validation (confidence gating)
    ↓
[6] Calculation Node (deterministic)
    ↓
[7] Comparison Node (multi-card ranking)
    ↓
[8] Guardrail Node (9 safety checks)
    ↓
[9] Human Approval (for transfers)
    ↓
[10] Final Answer (GPT-4o, grounded)
    ↓
LangSmith Trace + PostgreSQL Log
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Agent Framework | LangGraph (StateGraph) 0.4+ |
| Vector DB | PostgreSQL + pgvector (via Supabase) |
| Database Driver | `psycopg` (Pure Python) - ensures cross-platform stability |
| Connection Pooler | Supabase Transaction Pooler (NullPool via SQLAlchemy) |
| ORM | SQLAlchemy 2.0 |
| PDF Processing | PyMuPDF (fitz) |
| UI | Streamlit 1.41.0 (pinned for C-extension stability) |
| Backend API | FastAPI |
| Monitoring | LangSmith + PostgreSQL audit logging |
| Package Manager | `uv` (used for fast, deterministic builds) |
| Evaluation | Custom + RAGAS |

---

## Supported Cards

1. **Axis Atlas** — 5x EDGE Miles on travel/international
2. **HDFC Diners Club Black** — 10x on SmartBuy categories
3. **HDFC Infinia** — 10x on SmartBuy, unlimited
4. **Amex Platinum Travel** — 5x on travel/dining, milestone benefits
5. **SBI Cashback** — 5% online, 1% offline, simple cashback

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- OpenAI API key
- LangSmith account (free)

### 1. Clone & Install

```bash
git clone <repo-url>
cd "Intelligent Credit Card & Reward Optimization agent"
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env and fill in:
# - OPENAI_API_KEY
# - DATABASE_URL
# - LANGCHAIN_API_KEY
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb credit_card_rewards

# Run schema
psql -U postgres -d credit_card_rewards -f database/schema.sql
```

### 4. Generate Synthetic Card PDFs

```bash
python data/generate_synthetic_cards.py
```

### 5. Run Ingestion Pipeline

```bash
python rag/ingest_pdfs.py    # Extract text from PDFs
# Chunk + embed is done in the Streamlit Pipeline tab
```

Or run end-to-end:
```python
from rag.ingest_pdfs import ingest_all_pdfs
from rag.chunk_documents import chunk_all_cards
from rag.embed_documents import embed_all_cards

results = ingest_all_pdfs()
chunked = chunk_all_cards(results)
embed_all_cards(results, chunked)
```

### 6. Launch the App

```bash
streamlit run app/streamlit_app.py
```

Or launch the FastAPI backend:
```bash
uvicorn backend.main:app --reload
```

---

## Running Tests & Evaluation

```bash
# Unit tests (calculator)
pytest tests/test_calculator.py -v

# Calculation evaluation
python evaluation/calculation_eval.py

# Hallucination check
python evaluation/hallucination_eval.py
```

---

## Demo Flow (Capstone Demo)

1. **Show ingestion**: Pipeline tab → Generate PDFs → Run Ingestion
2. **Simple query**: *"I am spending Rs. 50,000 on flights. Which card?"*
3. **Show retrieved chunks** in the Sources expander
4. **Multi-turn**: *"My monthly spend is Rs. 40,000 travel, Rs. 30,000 dining. Optimize."*
5. **Transfer + HITL**: *"I have 80,000 EDGE Miles. Transfer to Air India?"* → Show approval
6. **Guardrail**: *"I am paying rent. Which card?"* → Agent cites exclusion
7. **Monitoring tab**: Show traces, latency, token usage, guardrail flags

---

## Project Deliverables

| # | Deliverable | Status |
|---|---|---|
| 1 | Working Streamlit app | ✅ |
| 2 | PostgreSQL + pgvector database | ✅ |
| 3 | PDF ingestion pipeline | ✅ |
| 4 | LangGraph agent (10 nodes) | ✅ |
| 5 | Deterministic calculator tool | ✅ |
| 6 | Card recommendation logic | ✅ |
| 7 | Human-in-the-loop approval | ✅ |
| 8 | Guardrail checks (9 rules) | ✅ |
| 9 | LangSmith monitoring | ✅ |
| 10 | Evaluation dataset + scripts | ✅ |
| 11 | Final project report | 📝 |
| 12 | Demo video | 🎥 |
| 13 | GitHub repository + README | ✅ |

---

## Folder Structure

```
credit-card-rewards-agent/
├── app/streamlit_app.py          # Full Streamlit UI
├── backend/
│   ├── main.py                   # FastAPI app
│   └── api_routes.py             # REST endpoints
├── agents/
│   ├── graph.py                  # LangGraph StateGraph
│   ├── nodes.py                  # All 10 graph nodes
│   ├── state.py                  # AgentState TypedDict
│   └── prompts.py                # All system prompts
├── tools/
│   ├── calculator.py             # Deterministic reward calculator
│   ├── retriever.py              # LangChain Tool wrapper
│   ├── rule_validator.py         # Retrieval confidence checker
│   └── transfer_calculator.py   # Transfer value calculator
├── rag/
│   ├── ingest_pdfs.py            # PDF text extraction
│   ├── chunk_documents.py        # Text chunking
│   ├── embed_documents.py        # OpenAI embeddings
│   └── retrieval.py              # Hybrid vector search
├── database/
│   ├── models.py                 # SQLAlchemy ORM
│   ├── db.py                     # Connection management
│   └── schema.sql                # PostgreSQL schema
├── data/
│   ├── raw_pdfs/                 # Card PDF documents
│   ├── generate_synthetic_cards.py
│   ├── sample_queries.csv        # 20 test queries
│   └── golden_answers.csv        # Expected outputs
├── evaluation/
│   ├── calculation_eval.py       # Calculator accuracy
│   └── hallucination_eval.py     # Hallucination detection
├── monitoring/
│   ├── langsmith_config.py       # LangSmith setup
│   └── custom_logger.py          # PostgreSQL audit log
├── tests/
│   └── test_calculator.py        # Pytest unit tests
├── requirements.txt
└── .env.example
```

---

## Why This Project Stands Out

Most RAG projects only retrieve information and summarize it. This project:

1. **Retrieves** structured financial rules from card documents
2. **Calculates** exact INR reward values using a deterministic tool
3. **Compares** all cards and ranks them by effective return %
4. **Validates** retrieval confidence before answering
5. **Enforces** 9 guardrails to prevent hallucination
6. **Requests** human approval for irreversible financial decisions
7. **Monitors** every interaction with full trace and audit log

The difference between a basic chatbot and this agent:

> **Basic chatbot**: "Axis Atlas is good for travel."
>
> **This agent**: "For your Rs. 50,000 flight booking, Axis Atlas gives Rs. 2,500 estimated value (5% return) based on the retrieved travel reward rule from Page 2 of the card T&C. HDFC DCB gives Rs. 5,000 via SmartBuy bookings. Monthly cap of 25,000 bonus points applies for DCB. Assumes 1 point = Rs. 0.50. Please verify with your card issuer. Confidence: MEDIUM-HIGH."

---

## Cloud Deployment Architecture (Streamlit Cloud & Supabase)

To ensure maximum stability in cloud environments (like Streamlit Community Cloud), the following architectural decisions were implemented:

1. **Pure Python Database Driver**: The project uses `psycopg` in pure Python mode (rather than `psycopg-binary`). This eliminates `Segmentation fault` crashes caused by conflicting C-level OpenSSL extensions on older Linux kernels.
2. **Supabase Transaction Pooling**: When connecting to Supabase via port `6543`, the connection is handled by a server-side Transaction Pooler (Supavisor). To prevent dropped connections, SQLAlchemy is configured to use `NullPool`, deferring all pooling logic to the server.
3. **PyArrow Serialization Bypass**: The Streamlit monitoring logs bypass standard Pandas to PyArrow DataFrame conversion for complex JSON fields, instead feeding native Python string dictionaries directly to `st.dataframe`. This prevents C++ memory faults during data serialization.
4. **Secrets Hierarchy**: The application seamlessly falls back from `.env` files for local development to `st.secrets` for Streamlit Cloud deployment without requiring code changes.

---

*IITM Agentic AI Capstone Project — 2025*
