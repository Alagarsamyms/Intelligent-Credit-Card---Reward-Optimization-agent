"""
Unit tests for the deterministic calculator tool.
Run: pytest tests/test_calculator.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.calculator import (
    RewardInput, calculate_reward, compare_cards,
    annual_fee_recovery, format_comparison_table,
)


class TestCalculateReward:
    """Core calculator unit tests."""

    def test_basic_points_calculation(self):
        """Test: Rs. 50,000 on flights at 5 pts/100 = 2,500 pts = Rs. 2,500."""
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=50000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
        )
        result = calculate_reward(inp)
        assert result.base_points == 2500.0
        assert result.total_value_inr == 2500.0
        assert result.effective_return_pct == pytest.approx(0.05)
        assert not result.cap_applied
        assert not result.exclusion

    def test_cashback_calculation(self):
        """Test: Rs. 10,000 online spend at 5% cashback = Rs. 500."""
        inp = RewardInput(
            card_name="SBI Cashback",
            spend_amount=10000,
            reward_rate=5.0,
            reward_unit="cashback_pct",
        )
        result = calculate_reward(inp)
        assert result.base_points == 500.0
        assert result.total_value_inr == 500.0
        assert result.effective_return_pct == pytest.approx(0.05)

    def test_monthly_cap_enforcement(self):
        """Test: Cap limits points when monthly cap is almost exhausted."""
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=50000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
            monthly_cap_points=10000,
            monthly_used_points=8000,   # Only 2,000 headroom left
        )
        result = calculate_reward(inp)
        assert result.base_points == 2500.0
        assert result.cap_applied is True
        assert result.points_after_cap == 2000.0   # Capped at headroom
        assert result.total_value_inr == 2000.0

    def test_exclusion_returns_zero(self):
        """Test: Excluded categories return 0 reward."""
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=25000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            exclusion=True,
            exclusion_note="Insurance is excluded per Axis Atlas T&C",
        )
        result = calculate_reward(inp)
        assert result.exclusion is True
        assert result.total_value_inr == 0.0
        assert result.base_points == 0.0

    def test_milestone_triggered(self):
        """Test: Milestone bonus fires when annual spend crosses threshold."""
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=50000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
            milestone_spend=300000,
            milestone_bonus=2500,
            current_annual_spend=280000,  # 280k → +50k crosses 300k
        )
        result = calculate_reward(inp)
        assert result.milestone_triggered is True
        assert result.milestone_bonus == 2500.0
        assert result.total_points == 2500.0 + 2500.0  # base + bonus

    def test_milestone_not_triggered(self):
        """Test: Milestone bonus does NOT fire if threshold not crossed."""
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=10000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
            milestone_spend=300000,
            milestone_bonus=2500,
            current_annual_spend=100000,  # 100k → +10k = 110k, not crossing 300k
        )
        result = calculate_reward(inp)
        assert result.milestone_triggered is False
        assert result.milestone_bonus == 0.0

    def test_zero_spend(self):
        """Test: Zero spend returns zero reward."""
        inp = RewardInput(
            card_name="SBI Cashback",
            spend_amount=0,
            reward_rate=5.0,
            reward_unit="cashback_pct",
        )
        result = calculate_reward(inp)
        assert result.total_value_inr == 0.0
        assert result.effective_return_pct == 0.0

    def test_point_value_scaling(self):
        """Test: Point value affects INR conversion."""
        inp_1x = RewardInput(
            card_name="Axis Atlas",
            spend_amount=10000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
        )
        inp_half = RewardInput(
            card_name="HDFC DCB",
            spend_amount=10000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=0.5,
        )
        r1 = calculate_reward(inp_1x)
        r2 = calculate_reward(inp_half)
        assert r1.total_value_inr == 2 * r2.total_value_inr


class TestCompareCards:
    """Multi-card comparison tests."""

    def test_best_card_is_first(self):
        """Best card by total_value_inr should be ranked first."""
        inputs = [
            RewardInput("SBI Cashback",  50000, 1.0, "cashback_pct"),
            RewardInput("Axis Atlas",    50000, 5.0, "points_per_100_inr", point_value_inr=1.0),
        ]
        results = compare_cards(inputs)
        assert results[0].card_name == "Axis Atlas"
        assert results[0].total_value_inr > results[1].total_value_inr

    def test_excluded_cards_ranked_last(self):
        """Excluded cards should appear after eligible cards."""
        inputs = [
            RewardInput("Axis Atlas", 25000, 0, "points_per_100_inr", exclusion=True, exclusion_note="Excluded"),
            RewardInput("SBI Cashback", 25000, 1.0, "cashback_pct"),
        ]
        results = compare_cards(inputs)
        assert results[-1].card_name == "Axis Atlas"
        assert results[-1].exclusion is True

    def test_comparison_table_format(self):
        """Comparison table should be a valid markdown string."""
        inputs = [
            RewardInput("Axis Atlas",  50000, 5.0, "points_per_100_inr", point_value_inr=1.0),
            RewardInput("SBI Cashback",50000, 1.0, "cashback_pct"),
        ]
        results = compare_cards(inputs)
        table = format_comparison_table(results, 50000)
        assert "Axis Atlas" in table
        assert "SBI Cashback" in table
        assert "| Rank |" in table


class TestAnnualFeeRecovery:
    """Annual fee recovery calculator tests."""

    def test_breakeven_calculation(self):
        """Fee of Rs. 5000, avg reward Rs. 5 per Rs. 100 → breakeven = Rs. 1,00,000."""
        result = annual_fee_recovery(
            annual_fee_inr=5000,
            avg_reward_value_per_100_inr=5.0,
        )
        assert result["breakeven_annual_spend"] == pytest.approx(100000.0)
        assert result["breakeven_monthly_spend"] == pytest.approx(100000 / 12, rel=0.01)

    def test_zero_reward_rate(self):
        """Zero reward rate should return None for breakeven."""
        result = annual_fee_recovery(5000, 0)
        assert result["breakeven_annual_spend"] is None


# ── Test Cases from Spec ──────────────────────────────────────────────────────
class TestSpecTestCases:
    """
    Exact test cases from the capstone spec.
    """

    def test_spec_case_1_50k_flights(self):
        """
        Spec Test 1: Rs. 50,000 on flights.
        Expected: Retrieve travel rules, compare cards, recommend best.
        Calculation check: At 5 pts/100, Rs. 50,000 → 2,500 pts = Rs. 2,500.
        """
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=50000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            point_value_inr=1.0,
            monthly_cap_points=10000,
        )
        result = calculate_reward(inp)
        assert result.total_value_inr == pytest.approx(2500.0)
        assert result.effective_return_pct == pytest.approx(0.05)

    def test_spec_case_2_insurance_exclusion(self):
        """
        Spec Test 2: Rs. 25,000 insurance premium.
        Expected: Exclusion detected → 0 reward.
        """
        inp = RewardInput(
            card_name="Axis Atlas",
            spend_amount=25000,
            reward_rate=5.0,
            reward_unit="points_per_100_inr",
            exclusion=True,
            exclusion_note="Insurance excluded per T&C",
        )
        result = calculate_reward(inp)
        assert result.exclusion is True
        assert result.total_value_inr == 0.0

    def test_spec_case_4_rent_exclusion(self):
        """
        Spec Test 4: Rent payment.
        Expected: Most cards exclude rent → should be flagged.
        """
        cards = [
            RewardInput("Axis Atlas", 20000, 0, "points_per_100_inr",
                        exclusion=True, exclusion_note="Rent excluded"),
            RewardInput("SBI Cashback", 20000, 0, "cashback_pct",
                        exclusion=True, exclusion_note="Rent excluded"),
        ]
        results = compare_cards(cards)
        for r in results:
            assert r.exclusion is True or r.total_value_inr == 0
