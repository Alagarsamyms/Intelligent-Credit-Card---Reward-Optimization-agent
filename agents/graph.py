"""
LangGraph Agent Graph — Full StateGraph with all 10 nodes and conditional edges.
Implements the complete agentic workflow for credit card reward optimization.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import AgentState
from agents.nodes import (
    user_input_node,
    intent_classification_node,
    clarification_node,
    retrieval_node,
    rule_validation_node,
    calculation_node,
    comparison_node,
    guardrail_node,
    human_approval_node,
    final_answer_node,
)

load_dotenv(override=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Conditional Edge Functions
# ═══════════════════════════════════════════════════════════════════════════════

def route_after_intent(state: AgentState) -> Literal["clarification", "retrieval"]:
    """After intent classification, check if we need to ask a clarifying question."""
    intent = state.get("intent", "unknown")
    # For complex intents, always check if clarification is needed
    if intent in ("point_transfer", "monthly_optimization"):
        return "clarification"
    # For simple intents, skip clarification if profile exists
    user_profile = state.get("user_profile", {})
    if user_profile.get("cards_owned"):
        return "retrieval"
    return "clarification"


def route_after_clarification(state: AgentState) -> Literal["retrieval", "end"]:
    """After clarification check, either proceed to retrieval or pause for user input."""
    if state.get("needs_clarification"):
        # In Streamlit, the graph pauses and the UI shows the question
        # We end the graph run — Streamlit will restart with the user's answer
        return "end"
    return "retrieval"


def route_after_validation(
    state: AgentState,
) -> Literal["calculation", "final_answer"]:
    """After validation, proceed to calculation or return insufficient info."""
    intent = state.get("intent", "unknown")
    sufficient = state.get("retrieval_sufficient", False)

    if not sufficient:
        return "final_answer"  # Will generate "insufficient info" response

    if intent in ("single_transaction", "monthly_optimization", "card_comparison"):
        return "calculation"
    elif intent == "point_transfer":
        return "calculation"
    else:
        return "final_answer"


def route_after_guardrail(
    state: AgentState,
) -> Literal["human_approval", "final_answer"]:
    """After guardrail check, route to human approval if needed or directly to final answer."""
    flags = state.get("guardrail_flags", [])
    needs_approval = any("TRANSFER_NEEDS_APPROVAL" in f for f in flags)

    if needs_approval:
        return "human_approval"
    return "final_answer"


def route_after_human_approval(
    state: AgentState,
) -> Literal["final_answer", "end"]:
    """After human approval node, check if user confirmed."""
    approved = state.get("human_approved")
    if approved is True:
        return "final_answer"
    elif approved is False:
        return "end"
    else:
        # Still awaiting — end the graph run (UI will restart after approval)
        return "end"


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Construction
# ═══════════════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Build and compile the full LangGraph StateGraph.

    Graph topology:
        START
          -> user_input
          -> intent_classification
          -> [clarification | retrieval]
        clarification
          -> [retrieval | END (await user input)]
        retrieval
          -> rule_validation
          -> [calculation | final_answer]
        calculation
          -> comparison
          -> guardrail
          -> [human_approval | final_answer]
        human_approval
          -> [final_answer | END]
        final_answer
          -> END
    """
    builder = StateGraph(AgentState)

    # ── Add nodes ─────────────────────────────────────────────────────────────
    builder.add_node("user_input", user_input_node)
    builder.add_node("intent_classification", intent_classification_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("rule_validation", rule_validation_node)
    builder.add_node("calculation", calculation_node)
    builder.add_node("comparison", comparison_node)
    builder.add_node("guardrail", guardrail_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("generate_final_answer", final_answer_node)

    # ── Add edges ─────────────────────────────────────────────────────────────
    builder.add_edge(START, "user_input")
    builder.add_edge("user_input", "intent_classification")

    builder.add_conditional_edges(
        "intent_classification",
        route_after_intent,
        {"clarification": "clarification", "retrieval": "retrieval"},
    )

    builder.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {"retrieval": "retrieval", "end": END},
    )

    builder.add_edge("retrieval", "rule_validation")

    builder.add_conditional_edges(
        "rule_validation",
        route_after_validation,
        {"calculation": "calculation", "final_answer": "generate_final_answer"},
    )

    builder.add_edge("calculation", "comparison")
    builder.add_edge("comparison", "guardrail")

    builder.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"human_approval": "human_approval", "final_answer": "generate_final_answer"},
    )

    builder.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {"final_answer": "generate_final_answer", "end": END},
    )

    builder.add_edge("generate_final_answer", END)

    # ── Compile with memory checkpointer for multi-turn conversations ─────────
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    return graph


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton graph instance
# ═══════════════════════════════════════════════════════════════════════════════
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_agent(
    query: str,
    user_id: str = "default_user",
    thread_id: str | None = None,
    user_profile: dict | None = None,
    human_approved: bool | None = None,
) -> dict:
    """
    Run the agent graph for a user query.

    Args:
        query: User's natural language question
        user_id: User identifier (for profile lookup)
        thread_id: Conversation thread ID (for multi-turn memory)
        user_profile: Optional user profile dict
        human_approved: True/False if this is a resumed run after approval

    Returns:
        Final agent state dict
    """
    graph = get_graph()
    thread_id = thread_id or user_id

    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "messages": [],
        "query": query,
        "intent": "unknown",
        "needs_clarification": False,
        "clarification_question": None,
        "retrieved_chunks": [],
        "retrieval_sufficient": False,
        "cards_to_compare": [],
        "spend_amount": None,
        "spend_category": None,
        "calculation_results": [],
        "user_id": user_id,
        "user_profile": user_profile or {},
        "awaiting_approval": False,
        "approval_context": None,
        "human_approved": human_approved,
        "guardrail_flags": [],
        "guardrail_passed": False,
        "final_answer": "",
        "recommended_card": None,
        "estimated_value_inr": None,
        "confidence": "MEDIUM",
        "start_time": None,
        "token_usage": {},
        "langsmith_run_id": None,
    }

    result = graph.invoke(initial_state, config=config)
    return result


if __name__ == "__main__":
    # Quick smoke test
    print("Testing agent graph...")
    result = run_agent(
        query="I am spending Rs. 50,000 on flights. Which card should I use?",
        user_id="test_user",
    )
    print("\n=== FINAL ANSWER ===")
    print(result.get("final_answer", "No answer generated"))
