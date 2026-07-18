import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.nodes import intent_classification_node, clarification_node
from agents.state import AgentState
from langchain_core.messages import HumanMessage

state = {
    "query": "I spend ₹1,00,000 per month on travel. Optimize my cards..",
    "messages": [HumanMessage(content="I spend ₹1,00,000 per month on travel. Optimize my cards..")],
    "user_profile": {
        "cards_owned": ["Axis Atlas", "HDFC Diners Club Black", "SBI Cashback"],
        "preferred_reward_type": "points",
        "point_valuation": {
            "Axis Atlas": 1.0,
            "HDFC Diners Club Black": 0.50,
            "HDFC Infinia": 1.0,
            "Amex Platinum Travel": 0.50,
            "SBI Cashback": 1.0,
        },
    }
}

print("Running Intent Node...")
intent_res = intent_classification_node(state)
print("Intent Output:", json.dumps(intent_res, default=str, indent=2))

state.update(intent_res)
state["messages"] = [HumanMessage(content="I spend ₹1,00,000 per month on travel. Optimize my cards..")]

print("\nRunning Clarification Node...")
clarif_res = clarification_node(state)
print("Clarification Output:", json.dumps(clarif_res, indent=2))
