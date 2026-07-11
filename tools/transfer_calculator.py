"""
Transfer Calculator Tool
Calculates the value of transferring reward points to partner programmes.
All calculations are deterministic — no LLM involved.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TransferInput:
    source_card: str
    points_to_transfer: float
    partner_name: str
    partner_type: str              # 'airline' or 'hotel'
    transfer_ratio: float          # partner units per source point (e.g., 0.5 means 2:1)
    minimum_points: int = 1000
    maximum_points: int | None = None
    # Assumed partner redemption value in INR per partner unit
    partner_unit_value_inr: float = 1.0
    # Alternative: direct redemption value per source point
    direct_value_inr: float | None = None


@dataclass
class TransferResult:
    source_card: str
    original_points: float
    partner_name: str
    partner_type: str
    transfer_ratio: float
    points_transferred: float = 0.0
    partner_units_received: float = 0.0
    estimated_value_inr: float = 0.0
    eligible: bool = True
    ineligibility_reason: str = ""
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_card":           self.source_card,
            "original_points":       self.original_points,
            "partner_name":          self.partner_name,
            "partner_type":          self.partner_type,
            "transfer_ratio":        self.transfer_ratio,
            "points_transferred":    round(self.points_transferred, 0),
            "partner_units_received": round(self.partner_units_received, 0),
            "estimated_value_inr":   round(self.estimated_value_inr, 2),
            "eligible":              self.eligible,
            "ineligibility_reason":  self.ineligibility_reason,
            "warnings":              self.warnings,
            "notes":                 self.notes,
        }

    def format_summary(self) -> str:
        if not self.eligible:
            return (
                f"**{self.partner_name}** ({self.partner_type}): ❌ Not eligible\n"
                f"  Reason: {self.ineligibility_reason}"
            )
        lines = [
            f"**{self.partner_name}** ({self.partner_type}):",
            f"  • Points transferred: {self.points_transferred:,.0f} from {self.source_card}",
            f"  • Partner units received: {self.partner_units_received:,.0f} {self.partner_type} points/miles",
            f"  • Transfer ratio: {1/self.transfer_ratio:.0f} source points → 1 partner unit",
            f"  • Estimated value: **Rs. {self.estimated_value_inr:,.0f}**",
        ]
        for w in self.warnings:
            lines.append(f"  • ⚠️ {w}")
        for n in self.notes:
            lines.append(f"  • ℹ️ {n}")
        return "\n".join(lines)


def calculate_transfer(inp: TransferInput) -> TransferResult:
    """
    Calculate the value of a point transfer to a loyalty programme partner.

    Enforces:
    - Minimum transfer requirements
    - Maximum transfer limits
    - Transfer ratio calculation
    - Estimated redemption value
    """
    result = TransferResult(
        source_card=inp.source_card,
        original_points=inp.points_to_transfer,
        partner_name=inp.partner_name,
        partner_type=inp.partner_type,
        transfer_ratio=inp.transfer_ratio,
    )

    # ── Minimum check ─────────────────────────────────────────────────────────
    if inp.points_to_transfer < inp.minimum_points:
        result.eligible = False
        result.ineligibility_reason = (
            f"Minimum transfer of {inp.minimum_points:,} points not met. "
            f"You have {inp.points_to_transfer:,.0f} points."
        )
        return result

    # ── Maximum check ─────────────────────────────────────────────────────────
    points_to_use = inp.points_to_transfer
    if inp.maximum_points and points_to_use > inp.maximum_points:
        points_to_use = inp.maximum_points
        result.warnings.append(
            f"Transfer capped at {inp.maximum_points:,} points (maximum limit). "
            f"Remaining {inp.points_to_transfer - inp.maximum_points:,.0f} points not transferred."
        )

    # ── Must transfer in multiples of minimum ─────────────────────────────────
    rounded_points = (points_to_use // inp.minimum_points) * inp.minimum_points
    if rounded_points < points_to_use:
        result.warnings.append(
            f"Transfer rounded down to {rounded_points:,.0f} points "
            f"(must be in multiples of {inp.minimum_points:,})."
        )

    result.points_transferred = rounded_points

    # ── Partner units calculation ─────────────────────────────────────────────
    partner_units = rounded_points * inp.transfer_ratio
    result.partner_units_received = partner_units

    # ── Estimated INR value ───────────────────────────────────────────────────
    estimated_value = partner_units * inp.partner_unit_value_inr
    result.estimated_value_inr = estimated_value

    result.notes.append(
        f"Assumed {inp.partner_type} point/mile value: Rs. {inp.partner_unit_value_inr:.2f} per unit"
    )
    result.warnings.append(
        "⚠️ Point transfers are IRREVERSIBLE in most programmes. "
        "Please verify current partner ratios before initiating."
    )
    result.warnings.append(
        "⚠️ Actual redemption value depends on availability and redemption category "
        "(economy vs business, peak vs off-peak)."
    )

    return result


def compare_transfer_options(
    source_card: str,
    points: float,
    partner_options: list[dict],
) -> list[TransferResult]:
    """
    Compare multiple transfer partner options for the same points balance.

    Args:
        source_card: Name of the source card
        points: Points available to transfer
        partner_options: List of dicts with partner details

    Returns:
        List of TransferResult sorted by estimated_value_inr descending
    """
    results = []
    for opt in partner_options:
        inp = TransferInput(
            source_card=source_card,
            points_to_transfer=points,
            partner_name=opt["partner_name"],
            partner_type=opt["partner_type"],
            transfer_ratio=opt["transfer_ratio"],
            minimum_points=opt.get("minimum_points", 1000),
            maximum_points=opt.get("maximum_points"),
            partner_unit_value_inr=opt.get("partner_unit_value_inr", 1.0),
        )
        results.append(calculate_transfer(inp))

    eligible = sorted(
        [r for r in results if r.eligible],
        key=lambda r: r.estimated_value_inr,
        reverse=True,
    )
    ineligible = [r for r in results if not r.eligible]
    return eligible + ineligible
