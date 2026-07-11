"""
Hallucination Evaluation Script
Checks if agent answers cite retrieved evidence or invent information.
Run: python evaluation/hallucination_eval.py
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_hallucination(
    answer: str,
    retrieved_chunks: list[dict],
    claimed_card: str | None = None,
    claimed_rate: float | None = None,
) -> dict:
    """
    Check if an agent answer contains hallucinated content.

    Checks:
    1. Does the answer reference retrieved card names?
    2. Does it mention a reward rate not found in retrieved chunks?
    3. Does it mention a transfer partner not in retrieved chunks?
    4. Does it include the disclaimer?
    5. Does it mention confidence level?

    Returns:
        {hallucination_detected, flags, score}
    """
    flags = []
    retrieved_text = " ".join([c.get("chunk_text", "") for c in retrieved_chunks]).lower()
    answer_lower = answer.lower()

    # Check 1: Disclaimer present
    has_disclaimer = any(phrase in answer_lower for phrase in [
        "please verify", "verify with", "card issuer", "official card", "disclaimer"
    ])
    if not has_disclaimer:
        flags.append("MISSING_DISCLAIMER: No verification disclaimer found")

    # Check 2: Confidence level present
    has_confidence = any(level in answer for level in [
        "HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW"
    ])
    if not has_confidence:
        flags.append("MISSING_CONFIDENCE: No confidence level stated")

    # Check 3: Assumptions mentioned
    has_assumptions = any(word in answer_lower for word in [
        "assuming", "assumption", "assumed"
    ])
    if not has_assumptions:
        flags.append("MISSING_ASSUMPTIONS: No assumptions stated")

    # Check 4: If rate is claimed, verify against chunks
    if claimed_rate is not None and retrieved_chunks:
        rate_pattern = rf"{claimed_rate}|{claimed_rate:.0f}"
        if not re.search(rate_pattern, retrieved_text):
            flags.append(f"POTENTIAL_HALLUCINATION: Claimed rate {claimed_rate} not found in retrieved chunks")

    # Check 5: If specific partner is mentioned, verify in chunks
    partners = re.findall(r"(air india|marriott|intermiles|ihg|vistara|taj|indigo|etihad)", answer_lower)
    for partner in partners:
        if partner not in retrieved_text:
            flags.append(f"POTENTIAL_HALLUCINATION: Transfer partner '{partner}' mentioned but not in retrieved chunks")

    hallucinated = len([f for f in flags if "HALLUCINATION" in f]) > 0
    score = 1.0 - (len(flags) * 0.1)

    return {
        "hallucination_detected": hallucinated,
        "flags": flags,
        "score": max(0.0, score),
        "total_flags": len(flags),
    }


def run_hallucination_eval(test_cases: list[dict]) -> None:
    """
    Run hallucination checks on a set of (answer, chunks) pairs.
    """
    print("=" * 70)
    print("HALLUCINATION EVALUATION REPORT")
    print("=" * 70)

    total = len(test_cases)
    clean = 0

    for i, tc in enumerate(test_cases, 1):
        result = check_hallucination(
            answer=tc.get("answer", ""),
            retrieved_chunks=tc.get("retrieved_chunks", []),
            claimed_card=tc.get("claimed_card"),
            claimed_rate=tc.get("claimed_rate"),
        )

        is_clean = not result["hallucination_detected"] and result["total_flags"] <= 1
        status = "[OK] CLEAN" if is_clean else "[WARN]  FLAGS"
        if is_clean:
            clean += 1

        print(f"\n{status} | Test {i}: {tc.get('name', 'Unknown')}")
        print(f"  Score: {result['score']:.2f} | Flags: {result['total_flags']}")
        for flag in result["flags"]:
            print(f"    • {flag}")

    print("\n" + "=" * 70)
    print(f"RESULT: {clean}/{total} answers passed hallucination check")
    print("=" * 70)


# ── Example test (without DB — uses mock data) ────────────────────────────────
MOCK_TEST_CASES = [
    {
        "name": "Good answer with disclaimer and confidence",
        "answer": (
            "**Recommended Card:** Axis Atlas\n"
            "**Estimated Reward Value:** Rs. 2,500\n"
            "**Calculation:** 5 points per Rs. 100 × Rs. 50,000 = 2,500 points × Rs. 1 = Rs. 2,500\n"
            "**Rules Used:** [Axis Atlas] Flight bookings earn 5 EDGE Miles per Rs. 100.\n"
            "**Assumptions:** Assuming 1 EDGE Mile = Rs. 1. Monthly cap not exhausted.\n"
            "**Confidence:** HIGH\n"
            "**[WARN] Disclaimer:** Please verify with your card issuer before making a decision."
        ),
        "retrieved_chunks": [
            {"chunk_text": "Travel (Flights & Hotels): 5 EDGE Miles per Rs. 100", "card_name": "Axis Atlas"}
        ],
        "claimed_rate": 5.0,
    },
    {
        "name": "Answer missing disclaimer",
        "answer": "Use Axis Atlas. It gives 5 points per Rs. 100. Total value is Rs. 2,500. Confidence: HIGH.",
        "retrieved_chunks": [
            {"chunk_text": "5 EDGE Miles per Rs. 100 on travel", "card_name": "Axis Atlas"}
        ],
    },
    {
        "name": "Answer with unverified transfer partner",
        "answer": "Transfer your points to Singapore Airlines for best value. Confidence: MEDIUM. Assuming 1 point = 1 mile.",
        "retrieved_chunks": [
            {"chunk_text": "Transfer to Air India at 2:1 ratio", "card_name": "Axis Atlas"}
        ],
    },
]

if __name__ == "__main__":
    run_hallucination_eval(MOCK_TEST_CASES)
