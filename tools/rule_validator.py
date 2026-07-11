"""
Rule Validator Tool
Checks whether retrieved chunks contain sufficient evidence to answer.
Returns SUFFICIENT or INSUFFICIENT with a confidence assessment.
"""
import re
from dataclasses import dataclass


# Keywords that indicate a rule IS present in the chunk
REWARD_INDICATOR_PATTERNS = [
    r"\d+\s*(points?|miles?|cashback|rewards?)\s*(per|for|on)",
    r"earn\s+\d+",
    r"reward\s+rate",
    r"accelerated",
    r"\d+%\s*cashback",
    r"eligible\s+transactions?",
    r"not eligible",
    r"excluded",
    r"monthly\s+cap",
    r"annual\s+cap",
    r"milestone",
]

EXCLUSION_PATTERNS = [
    r"not eligible",
    r"excluded",
    r"no rewards?",
    r"0%\s*cashback",
    r"zero\s+reward",
    r"excluded\s+categor",
    r"ineligible",
]


@dataclass
class ValidationResult:
    sufficient: bool
    confidence: str           # HIGH / MEDIUM / LOW
    found_rules: list[str]    # Extracted rule snippets
    found_exclusions: list[str]
    found_caps: list[str]
    reason: str
    best_chunks: list[dict]   # Top chunks by relevance

    def to_dict(self) -> dict:
        return {
            "sufficient":       self.sufficient,
            "confidence":       self.confidence,
            "found_rules":      self.found_rules,
            "found_exclusions": self.found_exclusions,
            "found_caps":       self.found_caps,
            "reason":           self.reason,
        }


def validate_retrieval(
    chunks: list[dict],
    spend_category: str,
    min_similarity: float = 0.40,
    min_chunks: int = 1,
) -> ValidationResult:
    """
    Validate whether retrieved chunks contain sufficient evidence.

    Args:
        chunks: List of retrieved chunk dicts
        spend_category: The spend category being queried (e.g., 'flights')
        min_similarity: Minimum similarity score to consider a chunk relevant
        min_chunks: Minimum number of relevant chunks required

    Returns:
        ValidationResult with sufficient flag and confidence
    """
    if not chunks:
        return ValidationResult(
            sufficient=False,
            confidence="LOW",
            found_rules=[],
            found_exclusions=[],
            found_caps=[],
            reason="No chunks were retrieved. The card document may not be ingested.",
            best_chunks=[],
        )

    # Filter chunks above similarity threshold
    relevant = [c for c in chunks if c.get("similarity", 0) >= min_similarity]

    if len(relevant) < min_chunks:
        return ValidationResult(
            sufficient=False,
            confidence="LOW",
            found_rules=[],
            found_exclusions=[],
            found_caps=[],
            reason=(
                f"Retrieved chunks have low similarity scores (best: "
                f"{max(c.get('similarity', 0) for c in chunks):.2f}). "
                f"The retrieved content may not be relevant to '{spend_category}'."
            ),
            best_chunks=chunks[:3],
        )

    # Extract evidence from relevant chunks
    found_rules = []
    found_exclusions = []
    found_caps = []

    for chunk in relevant:
        text = chunk.get("chunk_text", "")
        text_lower = text.lower()

        # Check for reward indicators
        for pattern in REWARD_INDICATOR_PATTERNS:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Extract surrounding context (up to 200 chars)
                for match in re.finditer(pattern, text_lower):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 100)
                    snippet = text[start:end].strip()
                    if snippet not in found_rules:
                        found_rules.append(f"[{chunk['card_name']}] ...{snippet}...")

        # Check for exclusions
        for pattern in EXCLUSION_PATTERNS:
            if re.search(pattern, text_lower):
                # Find the sentence containing the exclusion
                sentences = text.split(". ")
                for sent in sentences:
                    if re.search(pattern, sent.lower()):
                        entry = f"[{chunk['card_name']}] {sent.strip()}"
                        if entry not in found_exclusions:
                            found_exclusions.append(entry)

        # Check for caps
        cap_matches = re.findall(
            r"(monthly|annual|quarterly)\s+(cap|limit|maximum).*?[\d,]+\s*(points?|miles?|cashback)",
            text_lower
        )
        for match in cap_matches:
            cap_text = " ".join(match)
            if cap_text not in found_caps:
                found_caps.append(f"[{chunk['card_name']}] {cap_text}")

    # Determine overall sufficiency
    has_rule = len(found_rules) > 0
    has_high_similarity = any(c.get("similarity", 0) >= 0.48 for c in relevant)
    category_mentioned = any(
        spend_category.lower() in c.get("chunk_text", "").lower() for c in relevant
    )

    if has_rule and has_high_similarity and category_mentioned:
        sufficient = True
        confidence = "HIGH"
        reason = f"Found {len(found_rules)} clear reward rule(s) with high similarity for '{spend_category}'."
    elif has_rule and (has_high_similarity or category_mentioned):
        sufficient = True
        confidence = "MEDIUM-HIGH"
        reason = f"Found relevant rules but some context may be missing for '{spend_category}'."
    elif has_rule:
        sufficient = True
        confidence = "MEDIUM"
        reason = f"Found rules but category match is partial for '{spend_category}'. Assumptions may be needed."
    else:
        sufficient = False
        confidence = "LOW"
        reason = (
            f"Retrieved chunks do not contain clear reward rules for '{spend_category}'. "
            f"Cannot provide a grounded answer."
        )

    # Check for explicit exclusion (highest priority)
    if found_exclusions and any(
        spend_category.lower() in exc.lower() for exc in found_exclusions
    ):
        sufficient = True  # We CAN answer — the answer is "excluded"
        confidence = "HIGH"
        reason = f"Category '{spend_category}' is explicitly excluded from rewards. This IS a valid answer."

    return ValidationResult(
        sufficient=sufficient,
        confidence=confidence,
        found_rules=found_rules[:5],
        found_exclusions=found_exclusions[:5],
        found_caps=found_caps[:5],
        reason=reason,
        best_chunks=relevant[:3],
    )
