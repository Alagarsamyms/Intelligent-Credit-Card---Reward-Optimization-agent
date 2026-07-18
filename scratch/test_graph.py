import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graph import run_agent

print("Running graph with point transfer query, providing hotel stay goal in query")
result = run_agent(
    query="I have 50,000 points on my Amex. I want to transfer them to Marriott for hotel stays.",
    user_id="test_user_transfer",
    user_profile={
        "cards_owned": ["Amex Platinum Travel"],
        "preferred_reward_type": "points"
    }
)

print("Awaiting Approval:", result.get("awaiting_approval"))
if result.get("awaiting_approval"):
    print("Approval Context:", result.get("approval_context"))
print("Final Answer:", result.get("final_answer"))
print("Guardrail Flags:", result.get("guardrail_flags"))
print("Intent:", result.get("intent"))
