"""
RAG Retrieval Evaluation Script
Measures Precision@K, Recall@K, MRR, and Context Relevance for the retriever.

This script can be run:
  - Locally:   python evaluation/rag_eval.py
  - Streamlit: called from the Pipeline tab's 'Run Evaluation' button

Each test case specifies a query and a list of 'expected_keywords' that
the retrieved chunks must contain to be considered relevant.
"""
import os
import sys
import json
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load secrets from Streamlit if running on Cloud ────────────────────────────
try:
    import streamlit as _st
    for _k, _v in _st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv(override=True)


# ── Retrieval Test Cases ────────────────────────────────────────────────────────
RAG_TEST_CASES = [
    {
        "query_id": 1,
        "query": "I am spending Rs. 50000 on flights. Which card should I use?",
        "expected_keywords": ["flight", "travel", "EDGE Miles", "accelerated", "5"],
        "expected_cards": ["Axis Atlas", "HDFC Infinia", "HDFC Diners Club Black"],
        "top_k": 5,
    },
    {
        "query_id": 2,
        "query": "I am paying Rs. 25000 insurance premium. Which card should I use?",
        "expected_keywords": ["insurance", "excluded", "not eligible", "exclusion"],
        "expected_cards": ["Axis Atlas", "HDFC Infinia"],
        "top_k": 5,
    },
    {
        "query_id": 3,
        "query": "I am spending Rs. 100000 on hotels and want Marriott points.",
        "expected_keywords": ["hotel", "Marriott", "transfer", "partner"],
        "expected_cards": ["Axis Atlas", "HDFC Infinia"],
        "top_k": 5,
    },
    {
        "query_id": 4,
        "query": "Which card is best for rent payment?",
        "expected_keywords": ["rent", "excluded", "not eligible", "not applicable"],
        "expected_cards": ["Axis Atlas", "HDFC Diners Club Black"],
        "top_k": 5,
    },
    {
        "query_id": 5,
        "query": "Which card gives the best return for Zomato orders?",
        "expected_keywords": ["Zomato", "10X", "dining", "SmartBuy", "partner"],
        "expected_cards": ["HDFC Diners Club Black"],
        "top_k": 5,
    },
    {
        "query_id": 6,
        "query": "I have 80000 EDGE Miles on Axis Atlas. Should I transfer them to Air India?",
        "expected_keywords": ["Air India", "transfer", "EDGE Miles", "partner", "ratio"],
        "expected_cards": ["Axis Atlas"],
        "top_k": 5,
    },
    {
        "query_id": 7,
        "query": "I am spending Rs. 50000 at a foreign merchant internationally.",
        "expected_keywords": ["international", "foreign", "5", "EDGE", "cross-currency"],
        "expected_cards": ["Axis Atlas"],
        "top_k": 5,
    },
    {
        "query_id": 8,
        "query": "Can I transfer my SBI Cashback points to any airline?",
        "expected_keywords": ["SBI Cashback", "cashback", "transfer", "partner"],
        "expected_cards": ["SBI Cashback"],
        "top_k": 5,
    },
    {
        "query_id": 9,
        "query": "I am spending Rs. 10000 on fuel. Which card is best?",
        "expected_keywords": ["fuel", "petrol", "surcharge", "waiver", "exclude"],
        "expected_cards": ["Axis Atlas", "HDFC Diners Club Black"],
        "top_k": 5,
    },
    {
        "query_id": 10,
        "query": "Which card has the best welcome bonus or joining benefit?",
        "expected_keywords": ["welcome", "joining", "bonus", "benefit", "milestone"],
        "expected_cards": ["Axis Atlas", "HDFC Infinia", "Amex Platinum Travel"],
        "top_k": 5,
    },
]


# ── Relevance Judging ─────────────────────────────────────────────────────────

def is_relevant(chunk: dict, expected_keywords: list[str], expected_cards: list[str]) -> bool:
    """
    A retrieved chunk is 'relevant' if:
      - Its card_name is in expected_cards, AND
      - Its chunk_text contains at least one expected keyword (case-insensitive).
    """
    text = chunk.get("chunk_text", "").lower()
    card = chunk.get("card_name", "")

    card_match = card in expected_cards
    keyword_match = any(kw.lower() in text for kw in expected_keywords)
    return card_match and keyword_match


# ── Metrics ────────────────────────────────────────────────────────────────────

def precision_at_k(retrieved: list[dict], expected_keywords: list[str],
                   expected_cards: list[str], k: int) -> float:
    """Fraction of top-K retrieved chunks that are relevant."""
    top_k = retrieved[:k]
    relevant = sum(1 for c in top_k if is_relevant(c, expected_keywords, expected_cards))
    return relevant / k if k > 0 else 0.0


def recall_at_k(retrieved: list[dict], expected_keywords: list[str],
                expected_cards: list[str], k: int) -> float:
    """
    Recall: what fraction of relevant cards are represented in top-K chunks.
    Simplified: at least one relevant chunk per expected_card in top-K.
    """
    top_k = retrieved[:k]
    relevant_cards_found = set(
        c["card_name"] for c in top_k
        if is_relevant(c, expected_keywords, expected_cards)
    )
    total_expected = len(expected_cards)
    return len(relevant_cards_found) / total_expected if total_expected > 0 else 0.0


def reciprocal_rank(retrieved: list[dict], expected_keywords: list[str],
                    expected_cards: list[str]) -> float:
    """
    MRR component: 1 / rank of first relevant document.
    Returns 0 if no relevant document is found.
    """
    for i, chunk in enumerate(retrieved, start=1):
        if is_relevant(chunk, expected_keywords, expected_cards):
            return 1.0 / i
    return 0.0


def context_relevance_score(retrieved: list[dict], query: str) -> float:
    """
    Heuristic context relevance: fraction of chunks that share any query word (>4 chars).
    """
    if not retrieved:
        return 0.0
    query_words = [w.lower() for w in query.split() if len(w) > 4]
    relevant = sum(
        1 for c in retrieved
        if any(w in c.get("chunk_text", "").lower() for w in query_words)
    )
    return relevant / len(retrieved)


# ── Main Evaluation Loop ────────────────────────────────────────────────────────

def run_rag_evaluation(verbose: bool = True) -> dict:
    """
    Run the full RAG retrieval evaluation.

    Returns:
        dict with per-test results and aggregate metrics.
    """
    try:
        from rag.retrieval import retrieve
    except ImportError as e:
        print(f"[ERROR] Could not import retrieval module: {e}")
        return {"error": str(e), "results": []}

    all_results = []
    precision_scores = []
    recall_scores = []
    mrr_scores = []
    context_scores = []

    if verbose:
        print("=" * 72)
        print("RAG RETRIEVAL EVALUATION REPORT")
        print("=" * 72)

    for tc in RAG_TEST_CASES:
        try:
            chunks = retrieve(tc["query"], top_k=tc["top_k"])
        except Exception as e:
            if verbose:
                print(f"\n[ERROR] TC{tc['query_id']}: Retrieval failed — {e}")
            all_results.append({
                "query_id": tc["query_id"],
                "error": str(e),
                "precision_at_k": 0.0,
                "recall_at_k": 0.0,
                "reciprocal_rank": 0.0,
                "context_relevance": 0.0,
            })
            continue

        k = tc["top_k"]
        p_k   = precision_at_k(chunks, tc["expected_keywords"], tc["expected_cards"], k)
        r_k   = recall_at_k(chunks, tc["expected_keywords"], tc["expected_cards"], k)
        rr    = reciprocal_rank(chunks, tc["expected_keywords"], tc["expected_cards"])
        ctx_r = context_relevance_score(chunks, tc["query"])

        precision_scores.append(p_k)
        recall_scores.append(r_k)
        mrr_scores.append(rr)
        context_scores.append(ctx_r)

        status = "✅ PASS" if p_k >= 0.4 else "⚠️  LOW"

        if verbose:
            print(f"\n{status} | TC{tc['query_id']}: {tc['query'][:60]}...")
            print(f"  Retrieved {len(chunks)} chunks")
            print(f"  Precision@{k}: {p_k:.2f} | Recall@{k}: {r_k:.2f} | "
                  f"RR: {rr:.2f} | CtxRel: {ctx_r:.2f}")
            for i, chunk in enumerate(chunks[:3], 1):
                rel = "✅" if is_relevant(chunk, tc["expected_keywords"], tc["expected_cards"]) else "❌"
                print(f"    [{i}] {rel} [{chunk['card_name']}] "
                      f"sim={chunk.get('similarity', 0):.3f} — "
                      f"{chunk['chunk_text'][:80]}...")

        all_results.append({
            "query_id":         tc["query_id"],
            "query":            tc["query"],
            "precision_at_k":   round(p_k, 4),
            "recall_at_k":      round(r_k, 4),
            "reciprocal_rank":  round(rr, 4),
            "context_relevance": round(ctx_r, 4),
            "chunks_retrieved": len(chunks),
        })

    # ── Aggregate Metrics ──────────────────────────────────────────────────────
    n = len(precision_scores)
    mean_precision = sum(precision_scores) / n if n else 0.0
    mean_recall    = sum(recall_scores) / n if n else 0.0
    mean_mrr       = sum(mrr_scores) / n if n else 0.0
    mean_ctx       = sum(context_scores) / n if n else 0.0

    aggregate = {
        "mean_precision_at_k": round(mean_precision, 4),
        "mean_recall_at_k":    round(mean_recall, 4),
        "MRR":                 round(mean_mrr, 4),
        "mean_context_relevance": round(mean_ctx, 4),
        "tests_run":           len(all_results),
        "tests_passed":        sum(1 for r in all_results if r.get("precision_at_k", 0) >= 0.4),
    }

    if verbose:
        print("\n" + "=" * 72)
        print("AGGREGATE METRICS")
        print("=" * 72)
        print(f"  Mean Precision@K : {mean_precision:.4f}")
        print(f"  Mean Recall@K    : {mean_recall:.4f}")
        print(f"  MRR              : {mean_mrr:.4f}")
        print(f"  Context Relevance: {mean_ctx:.4f}")
        print(f"  Tests Passed     : {aggregate['tests_passed']}/{aggregate['tests_run']}")
        print("=" * 72)

    return {"aggregate": aggregate, "results": all_results}


if __name__ == "__main__":
    results = run_rag_evaluation(verbose=True)
    # Optionally save JSON results
    out_path = os.path.join(os.path.dirname(__file__), "rag_eval_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[INFO] Full results saved to {out_path}")
    passed = results["aggregate"].get("tests_passed", 0)
    total  = results["aggregate"].get("tests_run", 0)
    sys.exit(0 if passed >= total // 2 else 1)
