"""
Calculation Evaluation Script
Verifies that the deterministic calculator produces exact correct outputs.
Run: python evaluation/calculation_eval.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.calculator import RewardInput, calculate_reward, compare_cards

# ── Test cases with known expected outputs ────────────────────────────────────
TEST_CASES = [
    {
        "name": "TC1: Rs. 50,000 flights on Axis Atlas (no cap)",
        "input": RewardInput(
            card_name="Axis Atlas", spend_amount=50000,
            reward_rate=5.0, reward_unit="points_per_100_inr",
            point_value_inr=1.0, monthly_cap_points=None,
        ),
        "expected": {"total_value_inr": 2500.0, "effective_return_pct": 0.05, "cap_applied": False},
    },
    {
        "name": "TC2: Rs. 50,000 flights on Axis Atlas (cap hit at 10k)",
        "input": RewardInput(
            card_name="Axis Atlas", spend_amount=200001,
            reward_rate=5.0, reward_unit="points_per_100_inr",
            point_value_inr=1.0, monthly_cap_points=10000,
        ),
        "expected": {"cap_applied": True, "points_after_cap": 10000.0, "total_value_inr": 10000.0},
    },
    {
        "name": "TC3: Rs. 10,000 online SBI Cashback at 5%",
        "input": RewardInput(
            card_name="SBI Cashback", spend_amount=10000,
            reward_rate=5.0, reward_unit="cashback_pct",
        ),
        "expected": {"total_value_inr": 500.0, "effective_return_pct": 0.05},
    },
    {
        "name": "TC4: Exclusion case — insurance on Axis Atlas",
        "input": RewardInput(
            card_name="Axis Atlas", spend_amount=25000,
            reward_rate=5.0, reward_unit="points_per_100_inr",
            exclusion=True, exclusion_note="Insurance excluded",
        ),
        "expected": {"exclusion": True, "total_value_inr": 0.0},
    },
    {
        "name": "TC5: HDFC DCB 10X on flights via SmartBuy (50 pts/150 INR)",
        "input": RewardInput(
            card_name="HDFC DCB", spend_amount=30000,
            reward_rate=50/1.5, reward_unit="points_per_100_inr",
            point_value_inr=0.50, monthly_cap_points=25000,
        ),
        "expected": {"total_value_inr": 5000.0},  # (50/1.5) * 300 = 10,000 pts * 0.5 = 5,000
    },
]


def run_evaluation():
    results = []
    passed = 0
    failed = 0

    print("=" * 70)
    print("CALCULATION EVALUATION REPORT")
    print("=" * 70)

    for tc in TEST_CASES:
        result = calculate_reward(tc["input"])
        expected = tc["expected"]

        tc_passed = True
        issues = []

        for key, expected_val in expected.items():
            actual_val = getattr(result, key, None)
            if isinstance(expected_val, float):
                if abs((actual_val or 0) - expected_val) > 0.01:
                    tc_passed = False
                    issues.append(f"  {key}: expected={expected_val}, got={actual_val}")
            else:
                if actual_val != expected_val:
                    tc_passed = False
                    issues.append(f"  {key}: expected={expected_val}, got={actual_val}")

        status = "[OK] PASS" if tc_passed else "[ERR] FAIL"
        print(f"\n{status} | {tc['name']}")
        if not tc_passed:
            for issue in issues:
                print(issue)
        else:
            print(f"  total_value_inr = Rs. {result.total_value_inr:,.2f} | return = {result.effective_return_pct*100:.2f}%")

        if tc_passed:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULT: {passed}/{len(TEST_CASES)} tests passed | {failed} failed")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
