"""
Agent Output Tests
Tests the final answer format, guardrail triggering, confidence levels,
and the hallucination checker against mock agent responses.

Run: pytest tests/test_agent_outputs.py -v

These tests are purely structural / unit-level (no LLM calls, no DB).
For end-to-end tests that call the live agent, set RUN_LIVE_TESTS=1.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Helpers ────────────────────────────────────────────────────────────────────

GOOD_ANSWER = """
**Recommended Card:** Axis Atlas
**Estimated Reward Value:** Rs. 2,500
**Calculation:**
  Spend amount = Rs. 50,000
  Reward rate = 5 EDGE Miles per Rs. 100
  Estimated points = 2,500
  Assumed point value = Rs. 1
  Estimated reward value = Rs. 2,500
  Effective return = 5%
**Why this card:**
  The retrieved card document states eligible flight bookings earn accelerated rewards.
**Comparison:**
  Axis Atlas: Rs. 2,500 estimated value
  SBI Cashback: Rs. 500 (1% cashback)
**Caps or Exclusions:** Monthly cap of 10,000 EDGE Miles applies.
**Assumptions:** Assuming 1 EDGE Mile = Rs. 1. Monthly cap not yet exhausted.
**Confidence:** MEDIUM-HIGH
**[WARN] Disclaimer:** Please verify with your card issuer before making any financial decisions.
"""

GOOD_CHUNKS = [
    {"chunk_text": "Travel (Flights & Hotels): 5 EDGE Miles per Rs. 100 spend", "card_name": "Axis Atlas"},
    {"chunk_text": "Monthly bonus EDGE Miles cap: 10,000 miles per month",        "card_name": "Axis Atlas"},
]

MOCK_INSUFFICIENT = "I do not have enough information to answer this query. Please rephrase."


# ── Tests: Answer Format Compliance ───────────────────────────────────────────

class TestAnswerFormat:
    """Check that good answers contain all required structural components."""

    def test_good_answer_has_recommended_card(self):
        assert "Recommended Card" in GOOD_ANSWER

    def test_good_answer_has_estimated_value(self):
        assert "Estimated Reward Value" in GOOD_ANSWER

    def test_good_answer_has_calculation(self):
        assert "Calculation" in GOOD_ANSWER

    def test_good_answer_has_confidence(self):
        assert any(level in GOOD_ANSWER for level in ["HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW"])

    def test_good_answer_has_disclaimer(self):
        assert any(p in GOOD_ANSWER.lower() for p in ["verify with", "card issuer", "please verify"])

    def test_good_answer_has_assumptions(self):
        assert any(w in GOOD_ANSWER.lower() for w in ["assuming", "assumption", "assumed"])

    def test_good_answer_mentions_alternatives(self):
        """A good answer should compare at least two cards."""
        card_names = ["Axis Atlas", "SBI Cashback", "HDFC", "Amex", "Infinia"]
        mentions = sum(1 for card in card_names if card in GOOD_ANSWER)
        assert mentions >= 2, f"Answer only mentions {mentions} card(s), expected >= 2"


# ── Tests: Guardrail Checks via Hallucination Evaluator ───────────────────────

class TestGuardrailChecks:
    """Test the hallucination evaluator's guardrail detection logic."""

    def test_clean_answer_passes_all_checks(self):
        from evaluation.hallucination_eval import check_hallucination
        result = check_hallucination(
            answer=GOOD_ANSWER,
            retrieved_chunks=GOOD_CHUNKS,
            claimed_rate=5.0,
        )
        assert result["hallucination_detected"] is False
        assert result["score"] >= 0.7

    def test_missing_disclaimer_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        answer_no_disclaimer = (
            "Use Axis Atlas. It gives 5 points per Rs. 100. "
            "Total value is Rs. 2,500. Confidence: HIGH. Assuming 1 point = Rs. 1."
        )
        result = check_hallucination(answer_no_disclaimer, GOOD_CHUNKS)
        flag_types = [f.split(":")[0] for f in result["flags"]]
        assert "MISSING_DISCLAIMER" in flag_types

    def test_missing_confidence_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        answer_no_conf = (
            "Recommended Card: Axis Atlas. Reward = Rs. 2,500. "
            "Assuming 1 mile = Rs. 1. Please verify with your card issuer."
        )
        result = check_hallucination(answer_no_conf, GOOD_CHUNKS)
        flag_types = [f.split(":")[0] for f in result["flags"]]
        assert "MISSING_CONFIDENCE" in flag_types

    def test_missing_assumptions_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        answer_no_assumptions = (
            "Recommended Card: Axis Atlas. Confidence: HIGH. "
            "Please verify with your card issuer."
        )
        result = check_hallucination(answer_no_assumptions, GOOD_CHUNKS)
        flag_types = [f.split(":")[0] for f in result["flags"]]
        assert "MISSING_ASSUMPTIONS" in flag_types

    def test_unverified_partner_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        answer_bad_partner = (
            "Transfer your points to Etihad Airways for the best value. "
            "Confidence: HIGH. Assuming 1 point = 1 mile. "
            "Please verify with your card issuer."
        )
        # Retrieved chunks only mention Air India — Etihad is present in the regex
        # but NOT in the retrieved chunks, so it should be flagged
        chunks = [{"chunk_text": "Transfer to Air India at 2:1 ratio", "card_name": "Axis Atlas"}]
        result = check_hallucination(answer_bad_partner, chunks)
        assert result["hallucination_detected"] is True

    def test_correct_rate_in_chunks_not_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        result = check_hallucination(
            answer=GOOD_ANSWER,
            retrieved_chunks=GOOD_CHUNKS,
            claimed_rate=5.0,  # 5 is present in the chunks
        )
        flag_types = [f.split(":")[0] for f in result["flags"]]
        assert "POTENTIAL_HALLUCINATION" not in flag_types

    def test_incorrect_rate_flagged(self):
        from evaluation.hallucination_eval import check_hallucination
        result = check_hallucination(
            answer=GOOD_ANSWER,
            retrieved_chunks=GOOD_CHUNKS,
            claimed_rate=99.0,  # 99 is NOT in the chunks
        )
        flag_types = [f.split(":")[0] for f in result["flags"]]
        assert "POTENTIAL_HALLUCINATION" in flag_types


# ── Tests: Insufficient-Info Refusal ─────────────────────────────────────────

class TestInsufficientInfoRefusal:
    """Agent should explicitly refuse when retrieval is insufficient."""

    def test_insufficient_answer_contains_refusal_phrase(self):
        refusal_phrases = [
            "not enough information",
            "insufficient",
            "do not have",
            "cannot answer",
            "unable to find",
        ]
        assert any(p in MOCK_INSUFFICIENT.lower() for p in refusal_phrases)

    def test_insufficient_answer_does_not_invent_card(self):
        card_names = ["Axis Atlas", "HDFC Diners", "HDFC Infinia", "Amex", "SBI Cashback"]
        for card in card_names:
            assert card not in MOCK_INSUFFICIENT, (
                f"Refusal answer should not mention card '{card}'"
            )


# ── Tests: Confidence Level Validation ───────────────────────────────────────

class TestConfidenceLevels:
    """Confidence must be one of the 4 allowed levels."""

    @pytest.mark.parametrize("answer,expected_has_confidence", [
        ("Recommended Card: Axis Atlas. Confidence: HIGH. Please verify.", True),
        ("Use this card. Confidence: MEDIUM-HIGH. Assuming 1 point = Rs. 1. Verify with issuer.", True),
        ("Use Axis Atlas. It gives good rewards.", False),
    ])
    def test_confidence_presence(self, answer, expected_has_confidence):
        has_confidence = any(
            level in answer for level in ["HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW"]
        )
        assert has_confidence == expected_has_confidence


# ── Tests: Guardrail Flag Parser ─────────────────────────────────────────────

class TestGuardrailFlags:
    """
    Tests for the rule_validator module's confidence gating.
    Ensures weak retrieval is correctly flagged.
    """

    def test_no_chunks_fails_validation(self):
        from tools.rule_validator import validate_retrieval
        result = validate_retrieval(chunks=[], spend_category="flights", min_similarity=0.40)
        assert result.sufficient is False

    def test_low_similarity_fails_validation(self):
        from tools.rule_validator import validate_retrieval
        weak_chunks = [
            {"chunk_id": "x", "card_name": "Axis Atlas",
             "chunk_text": "general terms and conditions", "similarity": 0.20},
        ]
        result = validate_retrieval(chunks=weak_chunks, spend_category="flights", min_similarity=0.40)
        assert result.sufficient is False

    def test_strong_chunks_pass_validation(self):
        from tools.rule_validator import validate_retrieval
        strong_chunks = [
            {"chunk_id": "1", "card_name": "Axis Atlas",
             "chunk_text": "Travel (Flights & Hotels): 5 EDGE Miles per Rs. 100 spend",
             "similarity": 0.82},
            {"chunk_id": "2", "card_name": "HDFC Infinia",
             "chunk_text": "Reward points for flight bookings: 5 points per Rs. 150",
             "similarity": 0.78},
        ]
        result = validate_retrieval(chunks=strong_chunks, spend_category="flights", min_similarity=0.40)
        assert result.sufficient is True

    def test_mixed_chunks_uses_best_similarity(self):
        """Validation should pass if ANY chunk meets the threshold."""
        from tools.rule_validator import validate_retrieval
        chunks = [
            {"chunk_id": "weak",   "card_name": "A", "chunk_text": "misc", "similarity": 0.15},
            {"chunk_id": "strong", "card_name": "B", "chunk_text": "earn 5 points per Rs 100 on flight bookings", "similarity": 0.75},
        ]
        result = validate_retrieval(chunks=chunks, spend_category="flights", min_similarity=0.40)
        assert result.sufficient is True


# ── Integration: Live Agent End-to-End ───────────────────────────────────────

LIVE = os.getenv("RUN_LIVE_TESTS", "0") == "1"
skip_if_no_live = pytest.mark.skipif(not LIVE, reason="RUN_LIVE_TESTS not set")


class TestAgentEndToEnd:
    """
    Full end-to-end agent tests requiring live DB + OpenAI API.
    Enable with: RUN_LIVE_TESTS=1 pytest tests/test_agent_outputs.py -v -k live
    """

    @skip_if_no_live
    def test_flight_query_returns_structured_answer(self):
        """Agent should respond with Recommended Card and Confidence for a flight query."""
        from agents.graph import run_agent
        result = run_agent("I am spending Rs. 50000 on flights. Which card should I use?")
        answer = result.get("final_answer", "")
        assert "Recommended Card" in answer or "Axis Atlas" in answer
        assert any(level in answer for level in ["HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW"])

    @skip_if_no_live
    def test_rent_query_returns_refusal_or_exclusion(self):
        """Rent query should surface exclusion info or refusal — never a bare recommendation."""
        from agents.graph import run_agent
        result = run_agent("Which card is best for rent payment?")
        answer = result.get("final_answer", "")
        refusal_keywords = ["excluded", "not eligible", "insufficient", "not enough", "no information"]
        assert any(kw in answer.lower() for kw in refusal_keywords), (
            f"Expected exclusion/refusal for rent query. Got: {answer[:200]}"
        )

    @skip_if_no_live
    def test_insurance_answer_mentions_exclusion(self):
        """Insurance premium query must surface the exclusion rule."""
        from agents.graph import run_agent
        result = run_agent("I am paying Rs. 25000 insurance premium. Which card to use?")
        answer = result.get("final_answer", "")
        assert any(w in answer.lower() for w in ["excluded", "exclusion", "not eligible"]), (
            f"Expected exclusion mention for insurance query. Got: {answer[:200]}"
        )
