"""
LangGraph Agent State Schema
Defines the full state that flows through all graph nodes.
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class CalcResult(TypedDict):
    card_name: str
    spend_amount: float
    reward_rate: float
    reward_unit: str
    base_points: float
    cap_applied: bool
    cap_value: float | None
    reward_value_inr: float
    effective_return_pct: float
    milestone_triggered: bool
    milestone_bonus: float
    total_points: float
    total_value_inr: float
    notes: str


class RetrievedChunk(TypedDict):
    chunk_id: str
    card_name: str
    chunk_text: str
    page_number: int
    similarity: float


class AgentState(TypedDict):
    # ── Conversation ─────────────────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]
    query: str                                  # Current user query

    # ── Intent & Routing ─────────────────────────────────────────────────────
    intent: Literal[
        "single_transaction",
        "monthly_optimization",
        "point_transfer",
        "card_comparison",
        "point_valuation",
        "unknown",
    ]
    needs_clarification: bool
    clarification_question: str | None

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieved_chunks: list[RetrievedChunk]
    retrieval_sufficient: bool                  # True = enough evidence found
    cards_to_compare: list[str]                 # Which cards are relevant

    # ── Calculations ──────────────────────────────────────────────────────────
    spend_amount: float | None
    spend_category: str | None
    calculation_results: list[CalcResult]       # One per card

    # ── User Profile ─────────────────────────────────────────────────────────
    user_id: str
    user_profile: dict                          # Loaded from user_profiles table

    # ── Human Approval ────────────────────────────────────────────────────────
    awaiting_approval: bool
    approval_context: str | None                # What the user is approving
    human_approved: bool | None                 # True/False/None

    # ── Guardrails ───────────────────────────────────────────────────────────
    guardrail_flags: list[str]                  # Any violations found
    guardrail_passed: bool

    # ── Output ───────────────────────────────────────────────────────────────
    final_answer: str
    recommended_card: str | None
    estimated_value_inr: float | None
    confidence: Literal["HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW"]

    # ── Monitoring ────────────────────────────────────────────────────────────
    start_time: float | None
    token_usage: dict
    langsmith_run_id: str | None
