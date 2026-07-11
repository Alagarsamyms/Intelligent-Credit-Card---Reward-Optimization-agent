"""
Reward Calculator Tool — Deterministic, no LLM
All financial calculations are done here, not inside the LLM response.

Functions:
- calculate_reward(): Core per-card reward calculation
- compare_cards(): Rank multiple cards for a transaction
- spend_allocation_optimizer(): Distribute monthly spend across cards
- annual_fee_recovery(): Compute break-even spend for a card's annual fee
- milestone_impact(): Estimate incremental milestone bonus value
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RewardInput:
    card_name: str
    spend_amount: float              # in INR
    reward_rate: float               # points per 100 INR, or cashback %
    reward_unit: Literal[
        "points_per_100_inr",
        "cashback_pct",
        "miles_per_100_inr",
    ]
    point_value_inr: float = 1.0     # 1 point = Rs. X
    monthly_cap_points: float | None = None   # None = no cap
    monthly_used_points: float = 0.0 # already earned this month
    exclusion: bool = False          # True = category excluded
    exclusion_note: str = ""
    milestone_spend: float | None = None      # trigger threshold
    milestone_bonus: float | None = None      # bonus points at threshold
    current_annual_spend: float = 0.0         # for milestone tracking


@dataclass
class RewardResult:
    card_name: str
    spend_amount: float
    reward_rate: float
    reward_unit: str
    base_points: float = 0.0
    cap_applied: bool = False
    cap_value: float | None = None
    points_after_cap: float = 0.0
    reward_value_inr: float = 0.0
    effective_return_pct: float = 0.0
    milestone_triggered: bool = False
    milestone_bonus: float = 0.0
    total_points: float = 0.0
    total_value_inr: float = 0.0
    exclusion: bool = False
    exclusion_note: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "card_name":             self.card_name,
            "spend_amount":          self.spend_amount,
            "reward_rate":           self.reward_rate,
            "reward_unit":           self.reward_unit,
            "base_points":           round(self.base_points, 2),
            "cap_applied":           self.cap_applied,
            "cap_value":             self.cap_value,
            "points_after_cap":      round(self.points_after_cap, 2),
            "reward_value_inr":      round(self.reward_value_inr, 2),
            "effective_return_pct":  round(self.effective_return_pct, 4),
            "milestone_triggered":   self.milestone_triggered,
            "milestone_bonus":       round(self.milestone_bonus, 2),
            "total_points":          round(self.total_points, 2),
            "total_value_inr":       round(self.total_value_inr, 2),
            "exclusion":             self.exclusion,
            "exclusion_note":        self.exclusion_note,
            "notes":                 self.notes,
        }

    def format_summary(self) -> str:
        """Human-readable single-card summary."""
        if self.exclusion:
            return (
                f"**{self.card_name}**: ❌ NOT ELIGIBLE\n"
                f"  Reason: {self.exclusion_note}"
            )
        lines = [
            f"**{self.card_name}**:",
            f"  • Spend: Rs. {self.spend_amount:,.0f}",
            f"  • Rate: {self.reward_rate} {self.reward_unit}",
            f"  • Base Points/Cashback: {self.base_points:,.1f}",
        ]
        if self.cap_applied:
            lines.append(f"  • ⚠️ Cap Applied: limited to {self.cap_value:,.0f} points")
        lines.append(f"  • Reward Value: **Rs. {self.total_value_inr:,.0f}**")
        lines.append(f"  • Effective Return: {self.effective_return_pct*100:.2f}%")
        if self.milestone_triggered:
            lines.append(f"  • 🎯 Milestone Bonus: +{self.milestone_bonus:,.0f} points")
        for note in self.notes:
            lines.append(f"  • ℹ️ {note}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Core Calculator
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_reward(inp: RewardInput) -> RewardResult:
    """
    Deterministic reward calculation for a single card and transaction.

    Handles:
    - Points per Rs. 100 calculations
    - Cashback percentage calculations
    - Monthly caps
    - Exclusions
    - Milestone detection
    """
    result = RewardResult(
        card_name=inp.card_name,
        spend_amount=inp.spend_amount,
        reward_rate=inp.reward_rate,
        reward_unit=inp.reward_unit,
    )

    # ── Exclusion check ───────────────────────────────────────────────────────
    if inp.exclusion:
        result.exclusion = True
        result.exclusion_note = inp.exclusion_note or "Category excluded from rewards"
        result.notes.append(f"Exclusion: {result.exclusion_note}")
        return result

    # ── Base calculation ───────────────────────────────────────────────────────
    if inp.reward_unit == "cashback_pct":
        # Direct cashback: rate is already a percentage (e.g., 5.0 = 5%)
        base_points = inp.spend_amount * (inp.reward_rate / 100.0)
        result.notes.append(f"Cashback: {inp.reward_rate}% of Rs. {inp.spend_amount:,.0f}")
    elif inp.reward_unit in ("points_per_100_inr", "miles_per_100_inr"):
        # Points: rate = X points per Rs. 100
        base_points = (inp.spend_amount / 100.0) * inp.reward_rate
        unit = "miles" if inp.reward_unit == "miles_per_100_inr" else "points"
        result.notes.append(
            f"{inp.reward_rate} {unit} per Rs. 100 × Rs. {inp.spend_amount:,.0f}"
        )
    else:
        raise ValueError(f"Unknown reward_unit: {inp.reward_unit}")

    result.base_points = base_points

    # ── Monthly cap enforcement ───────────────────────────────────────────────
    if inp.monthly_cap_points is not None:
        available_cap = max(0.0, inp.monthly_cap_points - inp.monthly_used_points)
        if base_points > available_cap:
            result.cap_applied = True
            result.cap_value = inp.monthly_cap_points
            points_after_cap = available_cap
            result.notes.append(
                f"Monthly cap of {inp.monthly_cap_points:,.0f} points reached. "
                f"Only {available_cap:,.0f} points credited (cap headroom remaining)."
            )
        else:
            points_after_cap = base_points
    else:
        points_after_cap = base_points

    result.points_after_cap = points_after_cap

    # ── Reward value in INR ───────────────────────────────────────────────────
    if inp.reward_unit == "cashback_pct":
        # For cashback, points ARE rupees
        reward_value = points_after_cap
        result.notes.append(f"Cashback credited directly: Rs. {reward_value:,.2f}")
    else:
        reward_value = points_after_cap * inp.point_value_inr
        result.notes.append(
            f"Point value assumed: Rs. {inp.point_value_inr} per point → "
            f"Rs. {reward_value:,.2f}"
        )

    result.reward_value_inr = reward_value

    # ── Milestone detection ───────────────────────────────────────────────────
    milestone_bonus = 0.0
    if inp.milestone_spend and inp.milestone_bonus:
        new_annual_spend = inp.current_annual_spend + inp.spend_amount
        if (inp.current_annual_spend < inp.milestone_spend
                and new_annual_spend >= inp.milestone_spend):
            milestone_bonus = inp.milestone_bonus
            result.milestone_triggered = True
            result.notes.append(
                f"🎯 Annual milestone of Rs. {inp.milestone_spend:,.0f} reached! "
                f"Bonus: {milestone_bonus:,.0f} points"
            )

    result.milestone_bonus = milestone_bonus
    result.total_points = points_after_cap + milestone_bonus

    # ── Total value including milestone ──────────────────────────────────────
    if inp.reward_unit == "cashback_pct":
        result.total_value_inr = reward_value + (
            milestone_bonus * inp.point_value_inr if milestone_bonus else 0
        )
    else:
        result.total_value_inr = result.total_points * inp.point_value_inr

    # ── Effective return ──────────────────────────────────────────────────────
    if inp.spend_amount > 0:
        result.effective_return_pct = result.total_value_inr / inp.spend_amount
    else:
        result.effective_return_pct = 0.0

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-Card Comparison
# ═══════════════════════════════════════════════════════════════════════════════

def compare_cards(card_inputs: list[RewardInput]) -> list[RewardResult]:
    """
    Calculate rewards for multiple cards and rank them by total INR value.

    Returns:
        List of RewardResult sorted by total_value_inr descending (best first).
        Excluded cards appear at the bottom.
    """
    results = [calculate_reward(inp) for inp in card_inputs]
    # Sort: non-excluded first (by value desc), then excluded
    eligible = sorted(
        [r for r in results if not r.exclusion],
        key=lambda r: r.total_value_inr,
        reverse=True,
    )
    excluded = [r for r in results if r.exclusion]
    return eligible + excluded


def format_comparison_table(results: list[RewardResult], spend_amount: float) -> str:
    """Format comparison results as a readable table."""
    lines = [
        f"### Card Comparison for Rs. {spend_amount:,.0f} spend",
        "",
        "| Rank | Card | Reward Value | Return% | Cap Applied | Eligible |",
        "|------|------|-------------|---------|-------------|----------|",
    ]
    rank = 1
    for r in results:
        eligible = "✅" if not r.exclusion else "❌"
        rank_str = str(rank) if not r.exclusion else "—"
        lines.append(
            f"| {rank_str} | {r.card_name} | Rs. {r.total_value_inr:,.0f} | "
            f"{r.effective_return_pct*100:.2f}% | {'Yes' if r.cap_applied else 'No'} | {eligible} |"
        )
        if not r.exclusion:
            rank += 1

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Spend Allocation Optimizer
# ═══════════════════════════════════════════════════════════════════════════════

def spend_allocation_optimizer(
    monthly_spends: dict[str, float],
    available_cards: list[str],
    card_rules: dict[str, dict[str, RewardInput]],
) -> dict[str, dict]:
    """
    Optimize monthly spend allocation across cards and categories.

    Args:
        monthly_spends: {category: amount_inr}
        available_cards: List of cards the user owns
        card_rules: {card_name: {category: RewardInput}}

    Returns:
        {category: {best_card, result, all_results}}
    """
    allocation = {}
    for category, amount in monthly_spends.items():
        category_results = []
        for card in available_cards:
            if card in card_rules and category in card_rules[card]:
                inp = card_rules[card][category]
                inp.spend_amount = amount
                result = calculate_reward(inp)
                category_results.append(result)

        if not category_results:
            allocation[category] = {
                "best_card": None,
                "result": None,
                "all_results": [],
                "note": "No card rule found for this category",
            }
            continue

        ranked = compare_cards(category_results)
        best = ranked[0] if ranked else None
        allocation[category] = {
            "best_card": best.card_name if best and not best.exclusion else None,
            "result": best,
            "all_results": ranked,
        }

    return allocation


# ═══════════════════════════════════════════════════════════════════════════════
# Annual Fee Recovery Calculator
# ═══════════════════════════════════════════════════════════════════════════════

def annual_fee_recovery(
    annual_fee_inr: float,
    avg_reward_value_per_100_inr: float,
) -> dict:
    """
    Calculate the annual spend needed to break even on the annual fee.

    Args:
        annual_fee_inr: Annual fee (including GST if applicable)
        avg_reward_value_per_100_inr: Average reward value earned per Rs. 100 spent

    Returns:
        breakeven_spend: Annual spend needed to cover the fee
        monthly_breakeven: Monthly spend needed
    """
    if avg_reward_value_per_100_inr <= 0:
        return {
            "breakeven_annual_spend": None,
            "breakeven_monthly_spend": None,
            "note": "Cannot calculate — reward rate is zero or negative",
        }

    breakeven = (annual_fee_inr / avg_reward_value_per_100_inr) * 100
    return {
        "annual_fee_inr": annual_fee_inr,
        "avg_reward_per_100_inr": avg_reward_value_per_100_inr,
        "breakeven_annual_spend": round(breakeven, 2),
        "breakeven_monthly_spend": round(breakeven / 12, 2),
        "note": (
            f"You need to spend Rs. {breakeven:,.0f}/year "
            f"(Rs. {breakeven/12:,.0f}/month) to recover the annual fee."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Quick Test
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Test Case: Rs. 50,000 on flights
    inputs = [
        RewardInput(
            card_name="Axis Atlas",
            spend_amount=50000,
            reward_rate=5,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
            monthly_cap_points=10000,
            monthly_used_points=0,
        ),
        RewardInput(
            card_name="HDFC DCB",
            spend_amount=50000,
            reward_rate=50 / 3,     # 50 points per Rs. 150 = 33.33 per Rs. 100
            reward_unit="points_per_100_inr",
            point_value_inr=0.50,
            monthly_cap_points=25000,
        ),
        RewardInput(
            card_name="SBI Cashback",
            spend_amount=50000,
            reward_rate=1.0,        # 1% cashback (flights are offline)
            reward_unit="cashback_pct",
            monthly_cap_points=5000,
        ),
    ]

    results = compare_cards(inputs)
    for r in results:
        print(r.format_summary())
        print()

    print(format_comparison_table(results, 50000))
