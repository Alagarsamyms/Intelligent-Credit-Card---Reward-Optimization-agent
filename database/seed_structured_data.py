import os
import sys
import uuid
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db_context
from database.models import RewardRule, TransferPartner, UserProfile

CARD_RULES_DB = {
    "Axis Atlas": {
        "flights":    {"rate": 5.0, "unit": "points_per_100_inr", "cap": 10000, "point_val": 1.0},
        "hotels":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": 10000, "point_val": 1.0},
        "dining":     {"rate": 2.0, "unit": "points_per_100_inr", "cap": 5000,  "point_val": 1.0},
        "groceries":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "fuel":       {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "insurance":  {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance is excluded per Axis Atlas T&C"},
        "rent":       {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent is excluded per Axis Atlas T&C"},
        "utilities":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "general":    {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
    },
    "HDFC Diners Club Black": {
        "flights":    {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50, "note": "10X via SmartBuy"},
        "hotels":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50},
        "dining":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": 25000, "point_val": 0.50, "note": "Zomato/Swiggy 10X"},
        "groceries":  {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "fuel":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Fuel excluded from HDFC DCB rewards"},
        "insurance":  {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance excluded per HDFC DCB T&C"},
        "rent":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent excluded per HDFC DCB T&C"},
        "utilities":  {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "general":    {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
    },
    "HDFC Infinia": {
        "flights":    {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0, "note": "10X via SmartBuy"},
        "hotels":     {"rate": 50/1.5, "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "dining":     {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "groceries":  {"rate": 5/1.5,  "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "fuel":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Fuel not eligible per Infinia T&C"},
        "insurance":  {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance not eligible per Infinia T&C"},
        "rent":       {"rate": 0,       "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent not eligible per Infinia T&C"},
        "utilities":  {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
        "general":    {"rate": 5/1.5,   "unit": "points_per_100_inr", "cap": None,  "point_val": 1.0},
    },
    "Amex Platinum Travel": {
        "flights":    {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "hotels":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "dining":     {"rate": 5.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "groceries":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "fuel":       {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "insurance":  {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Insurance not eligible per Amex T&C"},
        "rent":       {"rate": 0,   "unit": "points_per_100_inr", "cap": None,  "exclusion": True, "exclusion_note": "Rent not eligible per Amex T&C"},
        "utilities":  {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
        "online":     {"rate": 3.0, "unit": "points_per_100_inr", "cap": 5000,  "point_val": 0.50},
        "general":    {"rate": 1.0, "unit": "points_per_100_inr", "cap": None,  "point_val": 0.50},
    },
    "SBI Cashback": {
        "flights":    {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Offline rate"},
        "hotels":     {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
        "dining":     {"rate": 5.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Online orders only"},
        "groceries":  {"rate": 5.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0, "note": "Online only"},
        "fuel":       {"rate": 1.0, "unit": "cashback_pct", "cap": 100,  "point_val": 1.0},
        "insurance":  {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
        "rent":       {"rate": 0,   "unit": "cashback_pct", "cap": None, "exclusion": True, "exclusion_note": "Rent not eligible per SBI Cashback T&C"},
        "utilities":  {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
        "general":    {"rate": 1.0, "unit": "cashback_pct", "cap": 5000, "point_val": 1.0},
    },
}

TRANSFER_PARTNERS_DB = [
    {"card": "Axis Atlas", "partner": "Marriott Bonvoy", "type": "hotel", "ratio": 2.0},
    {"card": "Axis Atlas", "partner": "Singapore Airlines KrisFlyer", "type": "airline", "ratio": 2.0},
    {"card": "HDFC Diners Club Black", "partner": "Marriott Bonvoy", "type": "hotel", "ratio": 0.5},
    {"card": "HDFC Diners Club Black", "partner": "Singapore Airlines KrisFlyer", "type": "airline", "ratio": 0.5},
    {"card": "HDFC Infinia", "partner": "Marriott Bonvoy", "type": "hotel", "ratio": 1.0},
    {"card": "HDFC Infinia", "partner": "Singapore Airlines KrisFlyer", "type": "airline", "ratio": 1.0},
    {"card": "Amex Platinum Travel", "partner": "Marriott Bonvoy", "type": "hotel", "ratio": 1.0},
]

def seed():
    print("Starting database seed...")
    with get_db_context() as db:
        # Clear existing data in these tables
        db.query(RewardRule).delete()
        db.query(TransferPartner).delete()
        
        # 1. Seed Reward Rules
        for card_name, categories in CARD_RULES_DB.items():
            for spend_cat, details in categories.items():
                rule = RewardRule(
                    card_name=card_name,
                    spend_category=spend_cat,
                    reward_rate=details.get("rate", 0),
                    reward_unit=details.get("unit", "points_per_100_inr"),
                    reward_type="points" if details.get("unit") != "cashback_pct" else "cashback",
                    cap_type="monthly" if details.get("cap") else None,
                    cap_value=details.get("cap"),
                    exclusion_flag=details.get("exclusion", False),
                    exclusion_notes=details.get("exclusion_note", ""),
                    confidence_score=1.0,
                    effective_date=datetime.utcnow()
                )
                db.add(rule)
        
        # 2. Seed Transfer Partners
        for tp in TRANSFER_PARTNERS_DB:
            partner = TransferPartner(
                card_name=tp["card"],
                partner_name=tp["partner"],
                partner_type=tp["type"],
                transfer_ratio=tp["ratio"],
                minimum_points=1000,
                effective_date=datetime.utcnow()
            )
            db.add(partner)

        # 3. Seed Default User Profile
        default_user_id = "default_user"
        existing_profile = db.query(UserProfile).filter_by(user_id=default_user_id).first()
        if not existing_profile:
            profile = UserProfile(
                user_id=default_user_id,
                cards_owned=["Axis Atlas", "HDFC Diners Club Black", "SBI Cashback"],
                preferred_reward_type="points",
                point_valuation={"Axis Atlas": 1.0, "HDFC Diners Club Black": 0.5, "SBI Cashback": 1.0, "HDFC Infinia": 1.0, "Amex Platinum Travel": 0.5},
                monthly_spend_pattern={"flights": 50000, "dining": 20000},
                preferred_partners=["Marriott Bonvoy"]
            )
            db.add(profile)
        
        db.commit()
        print("Successfully seeded reward_rules, transfer_partners, and user_profiles.")

if __name__ == "__main__":
    seed()
