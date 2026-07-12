"""
Streamlit App — Intelligent Credit Card & Rewards Optimization Agent
Full production UI with chat interface, human approval, monitoring, and sources panel.
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faulthandler
faulthandler.enable()

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

/* ══════════════════════════════════════════════
   DESIGN TOKENS — Dark theme (default)
══════════════════════════════════════════════ */
:root {
    --bg-base:          #0d0f1a;
    --bg-surface:       #111827;
    --bg-surface2:      #1a1f3c;
    --bg-surface3:      #1e2749;
    --border-subtle:    rgba(99,102,241,0.20);
    --border-accent:    rgba(99,102,241,0.40);
    --text-primary:     #e8eaf2;
    --text-secondary:   #94a3b8;
    --text-muted:       #64748b;
    --accent:           #818cf8;
    --accent2:          #c084fc;
    --accent3:          #fb7185;
    --btn-from:         #4f46e5;
    --btn-to:           #7c3aed;
    --btn-text:         #ffffff;
    --pill-bg:          rgba(99,102,241,0.12);
    --pill-border:      rgba(99,102,241,0.35);
    --pill-color:       #818cf8;
    --approval-bg:      #1c1a30;
    --approval-border:  rgba(251,146,60,0.55);
    --approval-title:   #fb923c;
    --sidebar-bg-from:  #0d1117;
    --sidebar-bg-to:    #111827;
    --sidebar-border:   rgba(99,102,241,0.15);
    --input-bg:         #1a1f3c;
    --input-border:     rgba(99,102,241,0.40);
    --input-color:      #e8eaf2;
    --hr-color:         rgba(99,102,241,0.15);
    --header-bg-from:   #1a1f3c;
    --header-bg-to:     #0d1117;
    --metric-value:     #818cf8;
}

/* ══════════════════════════════════════════════
   DESIGN TOKENS — Light theme overrides
══════════════════════════════════════════════ */
@media (prefers-color-scheme: light) {
    :root {
        --bg-base:          #f5f6fa;
        --bg-surface:       #ffffff;
        --bg-surface2:      #eef0fb;
        --bg-surface3:      #e5e7f8;
        --border-subtle:    rgba(79,70,229,0.15);
        --border-accent:    rgba(79,70,229,0.35);
        --text-primary:     #1e1e2e;
        --text-secondary:   #4b5563;
        --text-muted:       #6b7280;
        --accent:           #4f46e5;
        --accent2:          #7c3aed;
        --accent3:          #e11d48;
        --btn-from:         #4f46e5;
        --btn-to:           #7c3aed;
        --btn-text:         #ffffff;
        --pill-bg:          rgba(79,70,229,0.08);
        --pill-border:      rgba(79,70,229,0.30);
        --pill-color:       #4f46e5;
        --approval-bg:      #fff7ed;
        --approval-border:  rgba(234,88,12,0.45);
        --approval-title:   #ea580c;
        --sidebar-bg-from:  #f0f1fc;
        --sidebar-bg-to:    #e8eaf8;
        --sidebar-border:   rgba(79,70,229,0.12);
        --input-bg:         #ffffff;
        --input-border:     rgba(79,70,229,0.35);
        --input-color:      #1e1e2e;
        --hr-color:         rgba(79,70,229,0.12);
        --header-bg-from:   #eef0fb;
        --header-bg-to:     #f5f6fa;
        --metric-value:     #4f46e5;
    }
}

/* ── Global ── */
* { font-family: 'Inter', sans-serif; }

/* ── Main header ── */
.main-header {
    background: linear-gradient(135deg, var(--header-bg-from) 0%, var(--header-bg-to) 50%, var(--header-bg-from) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 60%);
    pointer-events: none;
}
.main-header h1 {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.main-header p {
    color: var(--text-secondary);
    font-size: 14px;
    margin: 6px 0 0 0;
}

/* ── Chat messages ── */
.user-message {
    background: linear-gradient(135deg, var(--bg-surface3), var(--bg-surface2));
    border: 1px solid var(--border-accent);
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 12px 0 4px auto;
    max-width: 80%;
    color: var(--text-primary);
    font-size: 15px;
}
.agent-message {
    background: linear-gradient(135deg, var(--bg-surface), var(--bg-surface2));
    border: 1px solid var(--border-subtle);
    border-radius: 4px 16px 16px 16px;
    padding: 18px 22px;
    margin: 4px auto 12px 0;
    max-width: 90%;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.7;
}

/* ── Confidence badges ── */
.badge-high       { background: rgba(34,197,94,0.13);  border: 1px solid #22c55e; color: #16a34a; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-medium-high{ background: rgba(59,130,246,0.13); border: 1px solid #3b82f6; color: #2563eb; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-medium     { background: rgba(234,179,8,0.13);  border: 1px solid #eab308; color: #a16207; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge-low        { background: rgba(239,68,68,0.13);  border: 1px solid #ef4444; color: #dc2626; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }

/* ── Approval panel ── */
.approval-panel {
    background: var(--approval-bg);
    border: 2px solid var(--approval-border);
    border-radius: 16px;
    padding: 24px;
    margin: 16px 0;
}
.approval-title {
    color: var(--approval-title);
    font-weight: 700;
    font-size: 16px;
    margin-bottom: 12px;
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(135deg, var(--bg-surface2), var(--bg-surface));
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 18px;
    text-align: center;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--metric-value);
}
.metric-label {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sidebar-bg-from) 0%, var(--sidebar-bg-to) 100%);
    border-right: 1px solid var(--sidebar-border);
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    color: var(--text-secondary);
}

/* ── Input boxes ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    color: var(--input-color) !important;
    border-radius: 12px !important;
    font-size: 15px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--btn-from), var(--btn-to)) !important;
    color: var(--btn-text) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(79,70,229,0.35) !important;
}

/* ── Source chunk pill ── */
.source-pill {
    display: inline-block;
    background: var(--pill-bg);
    border: 1px solid var(--pill-border);
    color: var(--pill-color);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 11px;
    margin: 2px;
}

/* ── Divider ── */
hr { border-color: var(--hr-color) !important; }
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

    if st.button("🔄 Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_approval = None
        st.session_state.pending_query = None
        st.rerun()

    st.divider()
    st.markdown("### 📊 Live Stats")
    try:
        sidebar_stats = get_monitoring_stats()
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st.metric("Queries", sidebar_stats["total_queries"])
            st.metric("Avg Latency", f"{int(sidebar_stats['avg_latency_ms'])} ms")
        with s_col2:
            st.metric("Avg Confidence", f"{sidebar_stats['avg_confidence']:.0%}")
            st.metric("Guardrail Flags", sidebar_stats["guardrail_violations"])
        st.caption("↑ Updates after each query")
    except Exception:
        st.caption("Stats unavailable — connect DB first")

    st.divider()
    db_ok = check_connection()
    status_color = "🟢" if db_ok else "🔴"
    st.caption(f"{status_color} Database: {'Connected' if db_ok else 'Disconnected'}")
    st.caption("🤖 Model: GPT-4o-mini | 📡 LangSmith: Active")


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
                with st.spinner("Analyzing rules & optimizing rewards..."):
                    try:
                        result = run_agent(
                            query=st.session_state.pending_query,
                            user_id=st.session_state.user_id,
                            thread_id=st.session_state.thread_id,
                            user_profile=st.session_state.user_profile,
                            human_approved=True,
                        )
                    except Exception as e:
                        import traceback
                        error_str = str(e)
                        if "postgresql://" in error_str:
                            import re
                            error_str = re.sub(r":.*@", ":***@", error_str)
                        st.error(f"**Database Connection Error:**\n\n{error_str}")
                        st.stop()
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

    # ── Quick sample queries ──────────────────────────────────────────────────
    st.markdown("##### 💡 Try a sample query:")
    sample_queries = [
        "I am spending Rs. 50,000 on flights. Which card should I use?",
        "I am paying Rs. 25,000 insurance premium. Which card should I use?",
        "I am spending Rs. 1,00,000 on hotels and want Marriott points.",
        "I have 80,000 EDGE Miles on Axis Atlas. Should I transfer them to Air India?",
        "My monthly spends are Rs. 40,000 travel, Rs. 30,000 dining, Rs. 20,000 groceries. Which cards should I use for each?",
    ]
    # Display as a 2-column grid so full text is visible
    sq_col1, sq_col2 = st.columns(2)
    for i, sq in enumerate(sample_queries):
        target_col = sq_col1 if i % 2 == 0 else sq_col2
        with target_col:
            if st.button(sq, key=f"sq_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sq})
                st.rerun()

    # Process the last user message if not yet answered
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_query = st.session_state.messages[-1]["content"]

        with st.spinner("🔍 Retrieving card rules and calculating..."):
            start_time = time.time()
            try:
                result = run_agent(
                    query=last_query,
                    user_id=st.session_state.user_id,
                    thread_id=st.session_state.thread_id,
                    user_profile=st.session_state.user_profile,
                )
            except Exception as e:
                error_str = str(e)
                if "postgresql://" in error_str:
                    import re
                    error_str = re.sub(r":.*@", ":***@", error_str)
                st.error(f"**Database Connection Error:**\n\n{error_str}")
                st.stop()
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
            display_cols = ["created_at", "query_text", "intent", "recommended_card",
                            "estimated_value_inr", "confidence_score", "latency_ms",
                            "guardrail_flags"]
            flat_logs = []
            for log in logs:
                flat = {}
                for k in display_cols:
                    if k in log:
                        val = str(log[k])
                        if k == "query_text" and len(val) > 60:
                            val = val[:60] + "..."
                        flat[k] = val
                flat_logs.append(flat)
            st.dataframe(flat_logs, use_container_width=True, height=400)
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
