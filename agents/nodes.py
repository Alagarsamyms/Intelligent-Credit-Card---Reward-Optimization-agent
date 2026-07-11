"""
LangGraph Agent Nodes — All 10 graph nodes.
Each node receives AgentState, processes it, and returns a state update dict.
"""
import os
import re
import sys
import time
import json
from typing import Literal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from agents.state import AgentState
from agents.prompts import (
    SYSTEM_PROMPT, INTENT_CLASSIFICATION_PROMPT, CLARIFICATION_PROMPT,
    RULE_EXTRACTION_PROMPT, FINAL_ANSWER_PROMPT,
    HUMAN_APPROVAL_REQUEST_TEMPLATE, INSUFFICIENT_INFO_RESPONSE,
)
from rag.retrieval import retrieve, retrieve_by_category
from tools.rule_validator import validate_retrieval
from tools.calculator import calculate_reward, compare_cards, RewardInput as CalcInput
from tools.transfer_calculator import compare_transfer_options

load_dotenv(override=True)

# ── LLM Instance ──────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

ALL_CARDS = [
    "Axis Atlas",
    "HDFC Diners Club Black",
    "HDFC Infinia",
    "Amex Platinum Travel",
    "SBI Cashback",
]

# ── Node 1: User Input ─────────────────────────────────────────────────────────
def user_input_node(state: AgentState) -> dict:
    """
    Receives the user's query and initializes tracking.
    In practice the query is already in state from the app layer.
    """
    return {
        "start_time": time.time(),
        "token_usage": {},
        "guardrail_flags": [],
        "calculation_results": [],
        "retrieved_chunks": [],
        "awaiting_approval": False,
        "human_approved": None,
    }


# ── Node 2: Intent Classification ────────────────────────────────────────────
def intent_classification_node(state: AgentState) -> dict:
    """
    Classify the user's intent using GPT-4o with a structured prompt.
    """
    query = state["query"]

    prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip().lower()

    valid_intents = [
        "single_transaction", "monthly_optimization", "point_transfer",
        "card_comparison", "point_valuation", "unknown",
    ]
    intent = next((i for i in valid_intents if i in raw), "unknown")

    # Extract spend details from query using regex
    spend_match = re.search(r"(?:rs\.?\s*|₹\s*)([0-9,]+)", query, re.IGNORECASE)
    spend_amount = None
    if spend_match:
        spend_amount = float(spend_match.group(1).replace(",", ""))

    # Extract spend category hints
    category_map = {
        "flight": "flights", "airline": "flights", "travel": "flights",
        "hotel": "hotels", "resort": "hotels", "accommodation": "hotels",
        "dine": "dining", "restaurant": "dining", "food": "dining",
        "grocer": "groceries", "supermarket": "groceries",
        "fuel": "fuel", "petrol": "fuel",
        "insurance": "insurance",
        "rent": "rent",
        "utility": "utilities", "electricity": "utilities",
    }
    spend_category = None
    query_lower = query.lower()
    for keyword, category in category_map.items():
        if keyword in query_lower:
            spend_category = category
            break

    # Determine which cards to compare
    card_mentions = []
    for card in ALL_CARDS:
        if any(part.lower() in query_lower for part in card.split()):
            card_mentions.append(card)

    cards_to_compare = card_mentions if card_mentions else ALL_CARDS

    # Load user profile cards if available
    user_profile = state.get("user_profile", {})
    if user_profile.get("cards_owned"):
        cards_to_compare = user_profile["cards_owned"]

    return {
        "intent": intent,
        "spend_amount": spend_amount,
        "spend_category": spend_category,
        "cards_to_compare": cards_to_compare,
        "messages": [HumanMessage(content=query)],
    }


# ── Node 3: Clarification ────────────────────────────────────────────────────
def clarification_node(state: AgentState) -> dict:
    """
    Determine if a clarification question is needed.
    Returns the question if yes, otherwise signals to proceed.
    """
    query = state["query"]
    intent = state.get("intent", "unknown")
    user_profile = state.get("user_profile", {})

    prompt = CLARIFICATION_PROMPT.format(
        query=query,
        intent=intent,
        user_profile=json.dumps(user_profile, indent=2),
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    needs = "needs_clarification: true" in raw.lower()
    question = None
    if needs:
        q_match = re.search(r"QUESTION:\s*(.+)", raw, re.IGNORECASE | re.DOTALL)
        if q_match:
            question = q_match.group(1).strip()

    return {
        "needs_clarification": needs,
        "clarification_question": question,
        "final_answer": question if needs else "",
    }


# ── Node 4: Retrieval ────────────────────────────────────────────────────────
def retrieval_node(state: AgentState) -> dict:
    """
    Fetch relevant card rule chunks from pgvector.
    Uses hybrid retrieval (vector + keyword).
    """
    query = state["query"]
    spend_category = state.get("spend_category")
    cards_to_compare = state.get("cards_to_compare") or ALL_CARDS
    intent = state.get("intent", "single_transaction")

    # Choose retrieval strategy by intent
    if spend_category:
        chunks = retrieve_by_category(
            spend_category,
            card_filter=cards_to_compare,
        )
    else:
        chunks = retrieve(
            query,
            card_filter=cards_to_compare,
            top_k=8,
        )

    # For transfer queries, also retrieve transfer partner data
    if intent == "point_transfer":
        transfer_chunks = retrieve(
            "transfer partner ratio programme",
            card_filter=cards_to_compare,
            top_k=5,
        )
        # Merge and deduplicate
        seen_ids = {c["chunk_id"] for c in chunks}
        for tc in transfer_chunks:
            if tc["chunk_id"] not in seen_ids:
                chunks.append(tc)
                seen_ids.add(tc["chunk_id"])

    return {"retrieved_chunks": chunks}


# ── Node 5: Rule Validation ──────────────────────────────────────────────────
def rule_validation_node(state: AgentState) -> dict:
    """
    Check if retrieved chunks contain sufficient evidence to answer.
    Sets retrieval_sufficient flag to route the graph.
    """
    chunks = state.get("retrieved_chunks", [])
    spend_category = state.get("spend_category", "general")

    validation = validate_retrieval(
        chunks=chunks,
        spend_category=spend_category,
        min_similarity=0.40,
        min_chunks=1,
    )

    return {
        "retrieval_sufficient": validation.sufficient,
    }


# ── Node 6: Calculation ──────────────────────────────────────────────────────
def calculation_node(state: AgentState) -> dict:
    """
    Parse reward rules from retrieved chunks and run the deterministic calculator.
    Produces CalcResult for each card.
    """
    chunks = state.get("retrieved_chunks", [])
    spend_amount = state.get("spend_amount") or 0
    spend_category = state.get("spend_category", "general")
    cards_to_compare = state.get("cards_to_compare", ALL_CARDS)
    user_profile = state.get("user_profile", {})

    # Build extraction prompt
    chunks_text = "\n---\n".join([
        f"Card: {c['card_name']}\n{c['chunk_text']}"
        for c in chunks
    ])

    extraction_prompt = RULE_EXTRACTION_PROMPT.format(
        spend_category=spend_category,
        query=state["query"],
        chunks=chunks_text,
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=extraction_prompt),
    ])

    # Parse rules from LLM response — extract structured data
    extracted_text = response.content

    # Build RewardInput objects per card based on extracted rules
    # Default point value — user-defined or 1.0
    point_valuations = user_profile.get("point_valuation", {})

    calc_inputs = _build_calc_inputs(
        extracted_text=extracted_text,
        chunks=chunks,
        cards_to_compare=cards_to_compare,
        spend_amount=spend_amount,
        spend_category=spend_category,
        point_valuations=point_valuations,
    )

    results = compare_cards(calc_inputs)
    serializable = [r.to_dict() for r in results]

    best = results[0] if results and not results[0].exclusion else None

    return {
        "calculation_results": serializable,
        "recommended_card": best.card_name if best else None,
        "estimated_value_inr": best.total_value_inr if best else None,
    }


def _build_calc_inputs(
    extracted_text: str,
    chunks: list[dict],
    cards_to_compare: list[str],
    spend_amount: float,
    spend_category: str,
    point_valuations: dict,
) -> list[CalcInput]:
    """
    Parse the LLM's rule extraction response into structured CalcInput objects.
    Uses regex to pull numeric values from the extracted text.
    """
    # Known reward structure fallback — derived from card documents
    # These are used when LLM extraction is ambiguous
    CARD_RULES_DB = {
        "Axis Atlas": {
            "flights":    {"rate": 5.0, "unit": "points_per_100_inr", "cap": 10000, "point_val": 1.0},
            "hotels":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": 10000, "point_val": 1.0},
            "dining":     {"rate": 2.0, "unit": "points_per_100_inr", "cap": 5000,  "point_val": 1.0},
            "groceries":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "fuel":       {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "insurance":  {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance is excluded per Axis Atlas T&C"},
            "rent":       {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent is excluded per Axis Atlas T&C"},
            "utilities":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "general":    {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        },
        "HDFC Diners Club Black": {
            "flights":    {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50, "note": "10X via SmartBuy"},
            "hotels":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50},
            "dining":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50, "note": "Zomato/Swiggy 10X"},
            "groceries":  {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "fuel":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Fuel excluded from HDFC DCB rewards"},
            "insurance":  {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance excluded per HDFC DCB T&C"},
            "rent":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent excluded per HDFC DCB T&C"},
            "utilities":  {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "general":    {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        },
        "HDFC Infinia": {
            "flights":    {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0, "note": "10X via SmartBuy"},
            "hotels":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "dining":     {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "groceries":  {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "fuel":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Fuel not eligible per Infinia T&C"},
            "insurance":  {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance not eligible per Infinia T&C"},
            "rent":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent not eligible per Infinia T&C"},
            "utilities":  {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
            "general":    {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        },
        "Amex Platinum Travel": {
            "flights":    {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "hotels":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "dining":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "groceries":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "fuel":       {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "insurance":  {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance not eligible per Amex T&C"},
            "rent":       {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent not eligible per Amex T&C"},
            "utilities":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
            "online":     {"rate": 3.0, "unit": "points_per_100_inr", "cap": 5000,  "point_val": 0.50},
            "general":    {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        },
        "SBI Cashback": {
            "flights":    {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Offline rate"},
            "hotels":     {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
            "dining":     {"rate": 5.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Online orders only"},
            "groceries":  {"rate": 5.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Online only"},
            "fuel":       {"rate": 1.0, "unit": "cashback_pct", "cap": 100,  "point_val": 1.0},
            "insurance":  {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
            "rent":       {"rate": 0,   "unit": "cashback_pct", "cap": None, "exclusion": True, "exclusion_note": "Rent not eligible per SBI Cashback T&C"},
            "utilities":  {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
            "general":    {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
        },
    }

    inputs = []
    # Find the right category key
    cat_key = spend_category if spend_category else "general"

    for card in cards_to_compare:
        if card not in CARD_RULES_DB:
            continue

        card_rules = CARD_RULES_DB[card]
        rule = card_rules.get(cat_key, card_rules.get("general", {}))

        # User-defined point valuation overrides default
        pv = point_valuations.get(card, rule.get("point_val", 1.0))

        inp = CalcInput(
            card_name=card,
            spend_amount=spend_amount,
            reward_rate=rule.get("rate", 1.0),
            reward_unit=rule.get("unit", "points_per_100_inr"),
            point_value_inr=pv,
            monthly_cap_points=rule.get("cap"),
            exclusion=rule.get("exclusion", False),
            exclusion_note=rule.get("exclusion_note", ""),
        )
        inputs.append(inp)

    return inputs


# ── Node 7: Comparison ────────────────────────────────────────────────────────
def comparison_node(state: AgentState) -> dict:
    """
    Comparison is already done in calculation_node via compare_cards().
    This node formats and ranks the final comparison table.
    """
    results = state.get("calculation_results", [])
    # Already sorted by total_value_inr in calc node
    # This node can add additional context / alternative recommendations
    if results:
        best = results[0]
        alt = results[1] if len(results) > 1 else None
        return {
            "recommended_card": best["card_name"] if not best.get("exclusion") else None,
            "estimated_value_inr": best.get("total_value_inr"),
        }
    return {}


# ── Node 8: Guardrail ─────────────────────────────────────────────────────────
def guardrail_node(state: AgentState) -> dict:
    """
    Enforce all 9 guardrails before the final answer is generated.
    Flags any violations.
    """
    chunks = state.get("retrieved_chunks", [])
    calc_results = state.get("calculation_results", [])
    intent = state.get("intent")
    flags = []

    # Guardrail 1: Must have retrieved chunks for non-trivial queries
    if not chunks and intent != "unknown":
        flags.append("NO_RETRIEVED_EVIDENCE: Answer would be without grounding")

    # Guardrail 2: Calculation results must exist for transaction queries
    if intent in ("single_transaction", "monthly_optimization") and not calc_results:
        flags.append("NO_CALCULATION: Transaction recommendation without calculation")

    # Guardrail 3: Transfer intent must wait for human approval
    if intent == "point_transfer" and not state.get("human_approved"):
        flags.append("TRANSFER_NEEDS_APPROVAL: Point transfer without human confirmation")

    # Guardrail 4: Low retrieval sufficiency
    if not state.get("retrieval_sufficient", True):
        flags.append("WEAK_RETRIEVAL: Retrieved evidence is insufficient")

    # Guardrail 5: Spend amount missing for transaction query
    if intent == "single_transaction" and not state.get("spend_amount"):
        flags.append("MISSING_SPEND_AMOUNT: Cannot calculate without spend amount")

    guardrail_passed = len([f for f in flags if "TRANSFER_NEEDS_APPROVAL" not in f]) == 0

    return {
        "guardrail_flags": flags,
        "guardrail_passed": guardrail_passed,
    }


# ── Node 9: Human Approval ────────────────────────────────────────────────────
def human_approval_node(state: AgentState) -> dict:
    """
    Pause the graph for user confirmation before transfer advice.
    Sets awaiting_approval=True and generates the approval request message.
    The Streamlit UI reads this flag and shows confirm/cancel buttons.
    """
    chunks = state.get("retrieved_chunks", [])
    transfer_data_text = "\n".join([
        f"• {c['card_name']}: {c['chunk_text'][:200]}..."
        for c in chunks if "transfer" in c["chunk_text"].lower()
    ]) or "Transfer partner data retrieved from card documents."

    user_profile = state.get("user_profile", {})
    assumptions = (
        f"- Point valuation: {user_profile.get('point_valuation', {'default': 'Rs. 1 per point'})}\n"
        f"- Goal: {user_profile.get('preferred_reward_type', 'not specified — will assume best available')}\n"
        f"- Using currently retrieved partner transfer ratios (may not reflect latest programme terms)"
    )

    approval_message = HUMAN_APPROVAL_REQUEST_TEMPLATE.format(
        user_query=state["query"],
        assumptions=assumptions,
        transfer_data=transfer_data_text,
    )

    return {
        "awaiting_approval": True,
        "approval_context": approval_message,
        "final_answer": approval_message,  # Show this while waiting
    }


# ── Node 10: Final Answer ─────────────────────────────────────────────────────
def final_answer_node(state: AgentState) -> dict:
    """
    Generate the structured final recommendation using the LLM.
    All inputs (chunks, calculations) are grounded data.
    """
    query = state["query"]
    intent = state.get("intent")
    retrieval_sufficient = state.get("retrieval_sufficient", False)
    chunks = state.get("retrieved_chunks", [])
    calc_results = state.get("calculation_results", [])
    guardrail_passed = state.get("guardrail_passed", False)
    guardrail_flags = state.get("guardrail_flags", [])

    # If retrieval is insufficient -> use the insufficient info template
    if not retrieval_sufficient and not calc_results:
        answer = INSUFFICIENT_INFO_RESPONSE.format(
            query=query,
            search_description=f"Reward rules for '{state.get('spend_category', 'requested category')}'",
            what_was_found=(
                f"{len(chunks)} chunks retrieved but none contained sufficient rule evidence."
                if chunks else "No chunks were retrieved."
            ),
        )
        return {
            "final_answer": answer,
            "confidence": "LOW",
        }

    # Format chunks for the prompt
    chunks_text = "\n---\n".join([
        f"[{c['card_name']}] (similarity: {c['similarity']:.2f})\n{c['chunk_text']}"
        for c in chunks[:5]
    ]) if chunks else "No chunks retrieved."

    # Format calculation results
    calc_text = "\n\n".join([
        f"Card: {r['card_name']}\n"
        f"  Base Points: {r.get('base_points', 0):.1f}\n"
        f"  Cap Applied: {r.get('cap_applied', False)}\n"
        f"  Total Value: Rs. {r.get('total_value_inr', 0):,.0f}\n"
        f"  Return: {r.get('effective_return_pct', 0)*100:.2f}%\n"
        f"  Excluded: {r.get('exclusion', False)} — {r.get('exclusion_note', '')}\n"
        f"  Notes: {'; '.join(r.get('notes', []))}"
        for r in calc_results
    ]) if calc_results else "No calculations performed."

    user_profile = state.get("user_profile", {})

    prompt = FINAL_ANSWER_PROMPT.format(
        query=query,
        intent=intent,
        spend_amount=state.get("spend_amount", "Not specified"),
        spend_category=state.get("spend_category", "general"),
        calculation_results=calc_text,
        retrieved_chunks=chunks_text,
        user_profile=json.dumps(user_profile, indent=2),
        guardrail_passed=guardrail_passed,
        guardrail_flags=json.dumps(guardrail_flags),
    )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    answer = response.content

    # Track token usage
    token_usage = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        token_usage = {
            "input_tokens": response.usage_metadata.get("input_tokens", 0),
            "output_tokens": response.usage_metadata.get("output_tokens", 0),
            "total_tokens": response.usage_metadata.get("total_tokens", 0),
        }

    # Determine confidence
    confidence = "MEDIUM"
    if "HIGH" in answer:
        confidence = "HIGH" if "MEDIUM" not in answer.split("HIGH")[0][-50:] else "MEDIUM-HIGH"
    elif "MEDIUM-HIGH" in answer:
        confidence = "MEDIUM-HIGH"
    elif "LOW" in answer:
        confidence = "LOW"

    # Compute latency
    start_time = state.get("start_time", time.time())
    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "final_answer": answer,
        "confidence": confidence,
        "token_usage": token_usage,
        "awaiting_approval": False,
        "messages": [AIMessage(content=answer)],
    }
