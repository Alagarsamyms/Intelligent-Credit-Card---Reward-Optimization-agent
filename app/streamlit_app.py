"""
Streamlit App — Intelligent Credit Card & Rewards Optimization Agent
Full production UI with chat interface, human approval, monitoring, and sources panel.
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from dotenv import load_dotenv

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Credit Card Rewards Agent",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv(override=True)

# ── LangSmith setup ───────────────────────────────────────────────────────────
from monitoring.langsmith_config import setup_langsmith
setup_langsmith()

from agents.graph import run_agent
from monitoring.custom_logger import log_recommendation, get_monitoring_stats, get_recent_logs
from database.db import check_connection

# ═══════════════════════════════════════════════════════════════════════════════
# Custom CSS — Premium Design
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global ── */
* { font-family: 'Inter', sans-serif; }
html, body, [class*="css"] { background-color: #0d0f1a; color: #e8eaf2; }

/* ── Main header ── */
.main-header {
    background: linear-gradient(135deg, #1a1f3c 0%, #0d1117 50%, #1a1f3c 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.main-header h1 {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8, #c084fc, #fb7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.main-header p {
    color: #94a3b8;
    font-size: 14px;
    margin: 6px 0 0 0;
}

/* ── Chat messages ── */
.user-message {
    background: linear-gradient(135deg, #1e2749, #1a1f3c);
    border: 1px solid rgba(99,102,241,0.4);
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 12px 0 4px auto;
    max-width: 80%;
    color: #e8eaf2;
    font-size: 15px;
}
.agent-message {
    background: linear-gradient(135deg, #111827, #1a1f3c);
    border: 1px solid rgba(148,163,184,0.15);
    border-radius: 4px 16px 16px 16px;
    padding: 18px 22px;
    margin: 4px auto 12px 0;
    max-width: 90%;
    color: #e8eaf2;
    font-size: 14px;
    line-height: 1.7;
}

/* ── Confidence badge ── */
.badge-high { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-medium-high { background: rgba(59,130,246,0.15); border: 1px solid #3b82f6; color: #3b82f6; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-medium { background: rgba(234,179,8,0.15); border: 1px solid #eab308; color: #eab308; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-low { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }

/* ── Approval panel ── */
.approval-panel {
    background: linear-gradient(135deg, #1c1a30, #1a1f3c);
    border: 2px solid rgba(251,146,60,0.5);
    border-radius: 16px;
    padding: 24px;
    margin: 16px 0;
}
.approval-title {
    color: #fb923c;
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 12px;
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(135deg, #1a1f3c, #111827);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 18px;
    text-align: center;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #818cf8;
}
.metric-label {
    font-size: 12px;
    color: #64748b;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
    border-right: 1px solid rgba(99,102,241,0.15);
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label { color: #94a3b8; }

/* ── Input box ── */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: #1a1f3c !important;
    border: 1px solid rgba(99,102,241,0.4) !important;
    color: #e8eaf2 !important;
    border-radius: 12px !important;
    font-size: 15px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(79,70,229,0.4) !important;
}

/* ── Source chunk pill ── */
.source-pill {
    display: inline-block;
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.3);
    color: #818cf8;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    margin: 2px;
}

/* ── Divider ── */
hr { border-color: rgba(99,102,241,0.15) !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Session State Initialization
# ═══════════════════════════════════════════════════════════════════════════════
def init_session():
    defaults = {
        "messages": [],          # Chat history: [{role, content, meta}]
        "user_id": "user_001",
        "thread_id": "thread_001",
        "user_profile": {
            "cards_owned": ["Axis Atlas", "HDFC Diners Club Black", "SBI Cashback"],
            "preferred_reward_type": "points",
            "point_valuation": {
                "Axis Atlas": 1.0,
                "HDFC Diners Club Black": 0.50,
                "HDFC Infinia": 1.0,
                "Amex Platinum Travel": 0.50,
                "SBI Cashback": 1.0,
            },
        },
        "pending_approval": None,  # Holds the approval context if awaiting
        "pending_query": None,
        "monitoring_data": [],
        "active_tab": "Chat",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar — User Profile & Settings
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.divider()

    st.markdown("### 👤 User Profile")
    user_id = st.text_input("User ID", value=st.session_state.user_id, key="uid_input")
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id

    st.markdown("**Cards Owned**")
    all_cards = ["Axis Atlas", "HDFC Diners Club Black", "HDFC Infinia", "Amex Platinum Travel", "SBI Cashback"]
    selected_cards = st.multiselect(
        "Select your cards",
        options=all_cards,
        default=st.session_state.user_profile.get("cards_owned", []),
        key="cards_selector",
    )
    st.session_state.user_profile["cards_owned"] = selected_cards

    reward_pref = st.selectbox(
        "Reward Preference",
        options=["points", "cashback", "miles", "hotel"],
        index=["points", "cashback", "miles", "hotel"].index(
            st.session_state.user_profile.get("preferred_reward_type", "points")
        ),
    )
    st.session_state.user_profile["preferred_reward_type"] = reward_pref

    st.divider()
    st.markdown("### 🔧 Quick Actions")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_approval = None
            st.session_state.pending_query = None
            st.rerun()
    with col2:
        if st.button("📊 Stats", use_container_width=True):
            st.session_state.active_tab = "Monitoring"
            st.rerun()

    st.divider()
    db_ok = check_connection()
    status_color = "🟢" if db_ok else "🔴"
    st.caption(f"{status_color} Database: {'Connected' if db_ok else 'Disconnected'}")
    st.caption("🤖 Model: GPT-4o | 📡 LangSmith: Active")


# ═══════════════════════════════════════════════════════════════════════════════
# Main Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <h1>💳 Credit Card Rewards Optimization Agent</h1>
    <p>Intelligent agentic AI • RAG • LangGraph • Multi-turn memory • Human-in-the-loop</p>
</div>
""", unsafe_allow_html=True)

# ── Tab Navigation ────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Monitoring", "⚡ Pipeline"])


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1: Chat Interface
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Display message history ───────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="user-message">🧑 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                meta = msg.get("meta", {})
                confidence = meta.get("confidence", "MEDIUM")
                badge_class = {
                    "HIGH": "badge-high",
                    "MEDIUM-HIGH": "badge-medium-high",
                    "MEDIUM": "badge-medium",
                    "LOW": "badge-low",
                }.get(confidence, "badge-medium")

                st.markdown(
                    f'<div class="agent-message">'
                    f'<span class="{badge_class}">{confidence}</span>&nbsp;&nbsp;'
                    f'💳 <strong>Agent</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(msg["content"])

                # Show retrieved sources
                if meta.get("retrieved_chunks"):
                    with st.expander(f"📚 Sources ({len(meta['retrieved_chunks'])} retrieved chunks)", expanded=False):
                        for i, chunk in enumerate(meta["retrieved_chunks"][:5], 1):
                            st.markdown(
                                f'<span class="source-pill">📄 {chunk.get("card_name", "Unknown")}</span>'
                                f'<span class="source-pill">pg. {chunk.get("page_number", "?")}</span>'
                                f'<span class="source-pill">sim: {chunk.get("similarity", 0):.2f}</span>',
                                unsafe_allow_html=True,
                            )
                            st.caption(chunk.get("chunk_text", "")[:250] + "...")
                            if i < min(5, len(meta["retrieved_chunks"])):
                                st.divider()

                # Latency & token info
                if meta.get("latency_ms"):
                    cols = st.columns(4)
                    cols[0].caption(f"⏱ {meta.get('latency_ms', 0)}ms")
                    token_data = meta.get("token_usage", {})
                    cols[1].caption(f"🔤 {token_data.get('total_tokens', 0)} tokens")
                    cols[2].caption(f"💡 {meta.get('intent', '—')}")
                    cols[3].caption(f"🃏 {meta.get('recommended_card', '—')}")

    # ── Human Approval Panel ──────────────────────────────────────────────────
    if st.session_state.pending_approval:
        st.markdown("""
        <div class="approval-panel">
            <div class="approval-title">⚠️ Human Approval Required</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.pending_approval)

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("✅ Confirm", key="confirm_btn", use_container_width=True):
                with st.spinner("Calculating transfer strategy..."):
                    result = run_agent(
                        query=st.session_state.pending_query,
                        user_id=st.session_state.user_id,
                        thread_id=st.session_state.thread_id,
                        user_profile=st.session_state.user_profile,
                        human_approved=True,
                    )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("final_answer", ""),
                    "meta": {
                        "confidence": result.get("confidence", "MEDIUM"),
                        "retrieved_chunks": result.get("retrieved_chunks", []),
                        "latency_ms": None,
                        "token_usage": result.get("token_usage", {}),
                        "intent": result.get("intent"),
                        "recommended_card": result.get("recommended_card"),
                    },
                })
                st.session_state.pending_approval = None
                st.session_state.pending_query = None
                st.rerun()

        with col2:
            if st.button("❌ Cancel", key="cancel_btn", use_container_width=True):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Transfer calculation cancelled. No changes have been made. "
                               "You can ask me something else.",
                    "meta": {"confidence": "HIGH"},
                })
                st.session_state.pending_approval = None
                st.session_state.pending_query = None
                st.rerun()

    # ── Quick sample queries ──────────────────────────────────────────────────
    st.divider()
    st.markdown("##### 💡 Try a sample query:")
    sample_queries = [
        "I am spending Rs. 50,000 on flights. Which card?",
        "Rs. 25,000 insurance premium. Which card?",
        "Which card is best for rent payment?",
        "I have 50,000 EDGE Miles. Should I transfer to Air India?",
        "My monthly spend: Rs. 40,000 travel, Rs. 30,000 dining. Optimize my cards.",
    ]
    cols = st.columns(len(sample_queries))
    for i, (col, sq) in enumerate(zip(cols, sample_queries)):
        with col:
            if st.button(sq[:35] + "...", key=f"sq_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sq})
                st.rerun()

    # ── Chat Input ────────────────────────────────────────────────────────────
    st.divider()
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Ask me about your credit card rewards",
            value="",
            placeholder="e.g. I am spending Rs. 50,000 on flights. Which card should I use?",
            height=80,
            key="chat_input",
        )
        submitted = st.form_submit_button("🚀 Send", use_container_width=True)

    if submitted and user_input.strip():
        query = user_input.strip()

        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": query})
        st.rerun()

    # Process the last user message if not yet answered
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_query = st.session_state.messages[-1]["content"]

        with st.spinner("🔍 Retrieving card rules and calculating..."):
            start_time = time.time()
            result = run_agent(
                query=last_query,
                user_id=st.session_state.user_id,
                thread_id=st.session_state.thread_id,
                user_profile=st.session_state.user_profile,
            )
            latency_ms = int((time.time() - start_time) * 1000)

        # Check if human approval is needed
        if result.get("awaiting_approval"):
            st.session_state.pending_approval = result.get("approval_context", "")
            st.session_state.pending_query = last_query
        else:
            # Log to DB
            try:
                log_recommendation(
                    user_id=st.session_state.user_id,
                    query_text=last_query,
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
                )
            except Exception:
                pass  # Don't fail the UI if logging fails

            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("final_answer", "Unable to generate a response."),
                "meta": {
                    "confidence": result.get("confidence", "MEDIUM"),
                    "retrieved_chunks": result.get("retrieved_chunks", []),
                    "latency_ms": latency_ms,
                    "token_usage": result.get("token_usage", {}),
                    "intent": result.get("intent"),
                    "recommended_card": result.get("recommended_card"),
                },
            })

        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2: Monitoring Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("## 📊 Monitoring Dashboard")

    try:
        stats = get_monitoring_stats()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['total_queries']}</div>
                <div class="metric-label">Total Queries</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['avg_latency_ms']:.0f}ms</div>
                <div class="metric-label">Avg Latency</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            conf_pct = round(stats['avg_confidence'] * 100, 1)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{conf_pct}%</div>
                <div class="metric-label">Avg Confidence</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['guardrail_violations']}</div>
                <div class="metric-label">Guardrail Flags</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("### 📋 Recent Logs")

        logs = get_recent_logs(limit=20)
        if logs:
            import pandas as pd
            df = pd.DataFrame(logs)
            display_cols = ["created_at", "query_text", "intent", "recommended_card",
                            "estimated_value_inr", "confidence_score", "latency_ms",
                            "guardrail_flags"]
            df_display = df[[c for c in display_cols if c in df.columns]]
            df_display["query_text"] = df_display["query_text"].str[:60] + "..."
            st.dataframe(df_display, use_container_width=True, height=400)
        else:
            st.info("No logs yet. Start a conversation to see monitoring data here.")
    except Exception as e:
        st.warning(f"Monitoring data unavailable: {e}")
        st.info("Connect to PostgreSQL and run some queries to see monitoring data.")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3: Pipeline Management
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("## ⚡ Data Pipeline")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 PDF Ingestion")
        st.info(
            "**Step 1**: Place credit card PDF documents in `data/raw_pdfs/`\n\n"
            "**Step 2**: Click 'Run Ingestion' to extract, chunk, and embed documents.\n\n"
            "The pipeline uses PyMuPDF for extraction -> RecursiveCharacterTextSplitter "
            "for chunking -> OpenAI text-embedding-3-small -> pgvector storage."
        )

        if st.button("🚀 Run Ingestion Pipeline", use_container_width=True, key="ingest_btn"):
            with st.spinner("Running ingestion pipeline..."):
                try:
                    from rag.ingest_pdfs import ingest_all_pdfs
                    from rag.chunk_documents import chunk_all_cards
                    from rag.embed_documents import embed_all_cards

                    progress = st.progress(0, text="Ingesting PDFs...")
                    ingestion_results = ingest_all_pdfs()
                    progress.progress(33, text="Chunking documents...")
                    chunked = chunk_all_cards(ingestion_results)
                    progress.progress(66, text="Generating embeddings...")
                    totals = embed_all_cards(ingestion_results, chunked)
                    progress.progress(100, text="Complete!")

                    st.success(
                        f"✅ Ingestion complete!\n"
                        f"Cards processed: {len(totals)}\n"
                        f"Total chunks: {sum(totals.values())}"
                    )
                    for card, count in totals.items():
                        st.caption(f"  • {card}: {count} chunks")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

    with col2:
        st.markdown("### 🃏 Generate Synthetic Cards")
        st.info(
            "Generate realistic synthetic credit card PDF documents for:\n"
            "- Axis Atlas\n"
            "- HDFC Diners Club Black\n"
            "- HDFC Infinia\n"
            "- Amex Platinum Travel\n"
            "- SBI Cashback\n\n"
            "These include reward structures, exclusions, caps, and transfer partners."
        )

        if st.button("📝 Generate Synthetic PDFs", use_container_width=True, key="gen_btn"):
            with st.spinner("Generating PDF documents..."):
                try:
                    import subprocess
                    result_proc = subprocess.run(
                        [sys.executable, "data/generate_synthetic_cards.py"],
                        capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
                    )
                    if result_proc.returncode == 0:
                        st.success("✅ 5 synthetic card PDFs generated in `data/raw_pdfs/`")
                        st.code(result_proc.stdout)
                    else:
                        st.error(f"Generation failed:\n{result_proc.stderr}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    st.markdown("### 🏗️ Architecture Overview")
    st.markdown("""
    ```
    User Query
        ↓
    [1] User Input Node
        ↓
    [2] Intent Classification (GPT-4o)
        ↓
    [3] Clarification Node (if needed)
        ↓
    [4] Retrieval Node (pgvector hybrid search)
        ↓
    [5] Rule Validation Node (confidence check)
        ↓
    [6] Calculation Node (deterministic calculator)
        ↓
    [7] Comparison Node (rank all eligible cards)
        ↓
    [8] Guardrail Node (9 safety checks)
        ↓
    [9] Human Approval Node (for transfers)  ←── User confirms/cancels
        ↓
    [10] Final Answer Node (GPT-4o with grounded context)
        ↓
    Structured Response + LangSmith Trace + PostgreSQL Log
    ```
    """)
