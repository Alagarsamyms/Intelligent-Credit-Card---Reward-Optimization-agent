"""
Synthetic Card PDF Generator
Generates realistic synthetic credit card T&C PDFs for 5 cards.
Based on publicly available reward structures for demonstration purposes.

Cards:
1. Axis Atlas Credit Card
2. HDFC Diners Club Black
3. HDFC Infinia
4. American Express Platinum Travel
5. SBI Cashback Card

Run: python data/generate_synthetic_cards.py
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "raw_pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Style helpers ────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def H1(text):
    return Paragraph(text, ParagraphStyle(
        "H1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=8, spaceBefore=12
    ))

def H2(text):
    return Paragraph(text, ParagraphStyle(
        "H2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#16213e"),
        spaceAfter=6, spaceBefore=10
    ))

def H3(text):
    return Paragraph(text, ParagraphStyle(
        "H3", parent=styles["Heading3"], fontSize=11, textColor=colors.HexColor("#0f3460"),
        spaceAfter=4, spaceBefore=8
    ))

def Body(text):
    return Paragraph(text, ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14,
        spaceAfter=4, alignment=TA_JUSTIFY
    ))

def BulletItem(text):
    return Paragraph(f"• {text}", ParagraphStyle(
        "Bullet", parent=styles["Normal"], fontSize=10, leading=14,
        leftIndent=16, spaceAfter=3
    ))

def table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 10),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4f4f8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f4f4f8"), colors.white]),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#ccccdd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ])

# ── Card 1: Axis Atlas ───────────────────────────────────────────────────────
def generate_axis_atlas():
    path = os.path.join(OUTPUT_DIR, "axis_atlas.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(H1("Axis Bank Atlas Credit Card"))
    story.append(Body("Terms and Conditions — Reward Programme | Effective Date: 1 January 2025"))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("1. Card Overview"))
    story.append(Body(
        "The Axis Bank Atlas Credit Card is a super-premium travel rewards credit card designed for "
        "frequent flyers and high-spend travellers. The card earns EDGE Miles on eligible transactions "
        "which can be redeemed against flight and hotel bookings or transferred to partner airline "
        "and hotel loyalty programmes."
    ))
    story.append(Body("Annual Fee: Rs. 5,000 + GST (waived on annual spend of Rs. 7,50,000 or more)"))
    story.append(Body("Welcome Benefit: 5,000 EDGE Miles on first transaction within 30 days."))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("2. Reward Earn Structure — EDGE Miles"))
    story.append(Body("Earn EDGE Miles on every eligible transaction as per the following structure:"))

    data = [
        ["Spend Category", "EDGE Miles Earned", "Notes"],
        ["International Transactions", "5 EDGE Miles per Rs. 100", "All foreign currency spends"],
        ["Travel (Flights & Hotels)", "5 EDGE Miles per Rs. 100", "Via eligible travel merchants"],
        ["Online Shopping", "2 EDGE Miles per Rs. 100", "Domestic e-commerce"],
        ["Dining", "2 EDGE Miles per Rs. 100", "Eligible restaurants"],
        ["Grocery", "1 EDGE Mile per Rs. 100", "Supermarkets and grocery stores"],
        ["Fuel", "1 EDGE Mile per Rs. 100", "Fuel surcharge waiver separately"],
        ["Utilities", "1 EDGE Mile per Rs. 100", "Electricity, water, telephone"],
        ["All Other Spends", "1 EDGE Mile per Rs. 100", "Eligible retail transactions"],
    ]
    story.append(Table(data, colWidths=[5.5*cm, 5.5*cm, 6*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("3. Monthly Reward Caps"))
    data = [
        ["Tier / Category", "Monthly Cap (EDGE Miles)"],
        ["Travel & International (5x)", "10,000 EDGE Miles per month"],
        ["Online & Dining (2x)", "5,000 EDGE Miles per month"],
        ["All other 1x categories", "No monthly cap"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("4. Milestone Benefits"))
    story.append(Body("Cardholders who meet annual spend milestones receive bonus EDGE Miles:"))
    data = [
        ["Annual Spend Milestone", "Bonus EDGE Miles"],
        ["Rs. 3,00,000", "2,500 EDGE Miles"],
        ["Rs. 7,50,000", "5,000 EDGE Miles + Annual Fee Waiver"],
        ["Rs. 15,00,000", "10,000 EDGE Miles"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("5. Exclusions — Transactions NOT Eligible for EDGE Miles"))
    exclusions = [
        "Insurance premium payments — No EDGE Miles earned",
        "Rent payments via any platform — Not eligible for accelerated rewards",
        "EMI transactions (converted from purchases) — Not eligible",
        "Fuel transactions above Rs. 10,000 per month",
        "Cash advance and cash withdrawal transactions",
        "Government and tax payments",
        "Wallet reloads (Paytm, PhonePe, Amazon Pay, etc.)",
        "Railway ticket bookings through IRCTC",
        "Utility bill payments — Earn only 1x (not accelerated)",
    ]
    for e in exclusions:
        story.append(BulletItem(e))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("6. Transfer Partners — EDGE Miles Transfer Ratios"))
    story.append(Body(
        "EDGE Miles can be transferred to the following airline and hotel loyalty programmes. "
        "Minimum transfer: 1,000 EDGE Miles. Processing time: 3–5 business days. "
        "Point transfers are irreversible once initiated."
    ))
    data = [
        ["Partner Programme", "Type", "Transfer Ratio (EDGE Miles : Partner Points/Miles)", "Min Transfer"],
        ["Air India Flying Returns",  "Airline", "2 EDGE Miles = 1 Flying Return Mile",  "1,000 EDGE Miles"],
        ["IndiGo 6E Rewards",         "Airline", "2 EDGE Miles = 1 6E Point",              "2,000 EDGE Miles"],
        ["Vistara Club Vistara",       "Airline", "2 EDGE Miles = 1 CV Point",              "1,000 EDGE Miles"],
        ["Marriott Bonvoy",            "Hotel",   "2.5 EDGE Miles = 1 Bonvoy Point",       "2,500 EDGE Miles"],
        ["IHG One Rewards",            "Hotel",   "2 EDGE Miles = 1 IHG Point",             "2,000 EDGE Miles"],
        ["Taj InnerCircle",            "Hotel",   "4 EDGE Miles = 1 Neupass Point",         "4,000 EDGE Miles"],
    ]
    story.append(Table(data, colWidths=[4.5*cm, 2.5*cm, 6.5*cm, 3.5*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("7. EDGE Miles Redemption Value"))
    story.append(Body(
        "1 EDGE Mile = Rs. 1 when redeemed via the Axis Bank rewards portal for flight/hotel bookings. "
        "When transferred to airline partners, the effective value depends on redemption class and availability. "
        "For cashback: 1 EDGE Mile = Rs. 0.25 (cashback conversion is at a lower ratio)."
    ))

    story.append(H2("8. Important Terms"))
    terms = [
        "EDGE Miles expire 3 years from the date of earning.",
        "Axis Bank reserves the right to modify reward structures with 30 days notice.",
        "Transactions will be categorised based on merchant category codes (MCC).",
        "The cardholder should verify merchant eligibility before assuming accelerated rewards.",
        "In case of any dispute, the bank's decision is final.",
    ]
    for t in terms:
        story.append(BulletItem(t))

    doc.build(story)
    print(f"[OK] Generated: {path}")


# ── Card 2: HDFC Diners Club Black ──────────────────────────────────────────
def generate_hdfc_dcb():
    path = os.path.join(OUTPUT_DIR, "hdfc_diners_club_black.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(H1("HDFC Bank Diners Club Black Credit Card"))
    story.append(Body("Reward Programme Terms and Conditions | Effective Date: 1 January 2025"))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("1. Card Overview"))
    story.append(Body(
        "The HDFC Bank Diners Club Black Credit Card is a ultra-premium card offering 10X reward points "
        "on select merchant categories, unlimited airport lounge access, and golf privileges. "
        "It is designed for high-net-worth individuals with significant monthly spends."
    ))
    story.append(Body("Annual Fee: Rs. 10,000 + GST"))
    story.append(Body("Fee Waiver: Annual fee waived if annual spend exceeds Rs. 8,00,000."))
    story.append(Body("Welcome Gift: 10,000 Reward Points on first transaction."))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("2. Base Reward Structure"))
    data = [
        ["Spend Category", "Reward Points Earned", "Notes"],
        ["All Retail Spends", "5 Points per Rs. 150 spent", "Base earn rate on all eligible transactions"],
    ]
    story.append(Table(data, colWidths=[5.5*cm, 5.5*cm, 6*cm], style=table_style()))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("3. 10X Reward Points — Accelerated Categories"))
    story.append(Body(
        "Earn 10X Reward Points (50 points per Rs. 150) on the following SmartBuy and partner categories. "
        "This is capped at 25,000 bonus points per calendar month."
    ))
    data = [
        ["10X Partner Category",     "Effective Rate",           "Monthly Cap"],
        ["Flights via SmartBuy",     "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["Hotels via SmartBuy",      "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["Myntra",                   "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["Amazon",                   "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["Swiggy",                   "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["Zomato",                   "50 Points per Rs. 150",   "25,000 bonus points/month"],
        ["BookMyShow",               "50 Points per Rs. 150",   "25,000 bonus points/month"],
    ]
    story.append(Table(data, colWidths=[5*cm, 5*cm, 7*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("4. Milestone Benefits"))
    data = [
        ["Quarterly Spend Milestone", "Milestone Benefit"],
        ["Rs. 1,50,000 in a quarter", "Weekend Getaway Voucher (Rs. 7,000 value)"],
        ["Rs. 3,00,000 in a quarter", "Weekend Getaway Voucher (Rs. 7,000) + Air India Voucher (Rs. 5,000)"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("5. Exclusions"))
    exclusions = [
        "Fuel transactions — Not eligible for reward points",
        "Insurance premium payments — Not eligible for reward points",
        "Rent payments — Not eligible for reward points",
        "EMI transactions — Points earned on original transaction only, not on EMI conversion",
        "Cash advances — Not eligible",
        "Utility bill payments — Eligible only at base rate (5 points per Rs. 150), not 10X",
        "Wallet reloads — Not eligible for any rewards",
        "Government fee and tax payments — Not eligible",
        "Flights NOT booked via HDFC SmartBuy — Earn only base rate, not 10X",
    ]
    for e in exclusions:
        story.append(BulletItem(e))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("6. Reward Point Valuation and Redemption"))
    data = [
        ["Redemption Option",       "Value per Point"],
        ["Airmiles (partner transfer)", "1 RP = 0.5 partner miles"],
        ["Flights via SmartBuy",    "1 RP = Rs. 0.50"],
        ["Hotels via SmartBuy",     "1 RP = Rs. 0.50"],
        ["Cashback",                "1 RP = Rs. 0.30"],
        ["Gift Vouchers",           "1 RP = Rs. 0.30"],
        ["Statement Credit",        "1 RP = Rs. 0.25"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("7. Transfer Partners"))
    story.append(Body("Reward Points can be transferred to the following programmes at the ratio of 2 Reward Points = 1 Airmile/Hotel Point:"))
    data = [
        ["Partner",                 "Type",    "Transfer Ratio",           "Min Transfer"],
        ["Air India Flying Returns","Airline",  "2 RP = 1 Flying Return",  "1,000 RP"],
        ["InterMiles",              "Airline",  "2 RP = 1 InterMile",      "1,000 RP"],
        ["Marriott Bonvoy",         "Hotel",    "2 RP = 1 Bonvoy Point",   "2,000 RP"],
        ["IHG One Rewards",         "Hotel",    "2 RP = 1 IHG Point",      "2,000 RP"],
    ]
    story.append(Table(data, colWidths=[4.5*cm, 2.5*cm, 6*cm, 4*cm], style=table_style()))

    doc.build(story)
    print(f"[OK] Generated: {path}")


# ── Card 3: HDFC Infinia ─────────────────────────────────────────────────────
def generate_hdfc_infinia():
    path = os.path.join(OUTPUT_DIR, "hdfc_infinia.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(H1("HDFC Bank Infinia Credit Card — Metal Edition"))
    story.append(Body("Reward Programme Terms and Conditions | Effective Date: 1 January 2025"))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("1. Card Overview"))
    story.append(Body(
        "HDFC Bank Infinia Credit Card (Metal) is HDFC's most exclusive card, offered by invitation. "
        "It earns 5 Reward Points per Rs. 150 on all spends with unlimited 10X on SmartBuy categories. "
        "Unlimited airport lounge access worldwide, concierge services, and golf privileges are included."
    ))
    story.append(Body("Annual Fee: Rs. 12,500 + GST"))
    story.append(Body("Fee Waiver: Waived on spend of Rs. 10,00,000 or more in the preceding year."))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("2. Reward Earn Structure"))
    data = [
        ["Spend Category",                "Reward Points Earned",           "Cap"],
        ["All Retail Spends (Base)",      "5 Points per Rs. 150 spent",    "No Cap"],
        ["SmartBuy — Flights",            "50 Points per Rs. 150 (10X)",   "Rs. 5,00,000 spend cap/month"],
        ["SmartBuy — Hotels",             "50 Points per Rs. 150 (10X)",   "Rs. 5,00,000 spend cap/month"],
        ["SmartBuy — Tanishq / Jewellery","50 Points per Rs. 150 (10X)",   "Rs. 5,00,000 spend cap/month"],
        ["International Transactions",    "5 Points per Rs. 150 spent",    "No Cap"],
        ["Dining",                        "5 Points per Rs. 150 spent",    "No Cap"],
        ["Insurance",                     "NOT ELIGIBLE — 0 Points",       "—"],
        ["Rent",                          "NOT ELIGIBLE — 0 Points",       "—"],
        ["Fuel",                          "NOT ELIGIBLE — 0 Points",       "—"],
        ["Wallet Reloads",                "NOT ELIGIBLE — 0 Points",       "—"],
    ]
    story.append(Table(data, colWidths=[5.5*cm, 5.5*cm, 6*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("3. Reward Point Valuation"))
    data = [
        ["Redemption Mode",          "Value per Reward Point"],
        ["Flights via SmartBuy",     "1 RP = Rs. 1.00"],
        ["Hotels via SmartBuy",      "1 RP = Rs. 1.00"],
        ["Airmiles Transfer",        "1 RP = 0.5 Airmile"],
        ["Cashback on Statement",    "1 RP = Rs. 0.50"],
        ["Gift Vouchers",            "1 RP = Rs. 0.50"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("4. Transfer Partners"))
    data = [
        ["Partner",                 "Type",    "Transfer Ratio",           "Min Transfer"],
        ["Air India Flying Returns","Airline",  "2 RP = 1 Flying Return",  "1,000 RP"],
        ["InterMiles",              "Airline",  "2 RP = 1 InterMile",      "1,000 RP"],
        ["Vistara Club Vistara",    "Airline",  "2 RP = 1 CV Point",       "1,000 RP"],
        ["Marriott Bonvoy",         "Hotel",    "2 RP = 1 Bonvoy Point",   "2,000 RP"],
        ["IHG One Rewards",         "Hotel",    "2 RP = 1 IHG Point",      "2,000 RP"],
        ["Accor Live Limitless",    "Hotel",    "4 RP = 1 Accor Point",    "4,000 RP"],
    ]
    story.append(Table(data, colWidths=[4.5*cm, 2.5*cm, 6*cm, 4*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("5. Important Terms and Exclusions"))
    story.append(Body(
        "HDFC Infinia Reward Points are valid for 3 years from the date of accrual. "
        "Points earned on transactions that are subsequently reversed will be forfeited. "
        "HDFC Bank may modify the reward structure with prior notice of 30 days."
    ))

    doc.build(story)
    print(f"[OK] Generated: {path}")


# ── Card 4: Amex Platinum Travel ─────────────────────────────────────────────
def generate_amex_platinum_travel():
    path = os.path.join(OUTPUT_DIR, "amex_platinum_travel.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(H1("American Express Platinum Travel Credit Card"))
    story.append(Body("Membership Rewards Programme | Terms and Conditions | Effective Date: 1 January 2025"))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("1. Card Overview"))
    story.append(Body(
        "The American Express Platinum Travel Credit Card earns Membership Rewards (MR) Points on all eligible "
        "spends. MR Points can be redeemed for Taj vouchers, IndiGo flight credits, or statement credits. "
        "The card includes complimentary Taj Epicure Club membership for premium hotel stays."
    ))
    story.append(Body("Annual Fee: Rs. 3,500 + GST (Year 1 waived as welcome offer)"))
    story.append(Body("Welcome Benefit: 10,000 MR Points + 1,000 bonus MR Points on 4 transactions in 60 days"))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("2. Reward Earn Structure"))
    data = [
        ["Spend Category",           "MR Points Earned",              "Cap"],
        ["Travel (Flights/Hotels)",  "5 MR Points per Rs. 100 spent", "No monthly cap"],
        ["Dining at partner restaurants","5 MR Points per Rs. 100",   "No monthly cap"],
        ["Online Spends",            "3 MR Points per Rs. 100 spent", "5,000 MR Points/month"],
        ["All Other Retail",         "1 MR Point per Rs. 100 spent",  "No cap"],
        ["Fuel",                     "1 MR Point per Rs. 100 spent",  "Surcharge waiver on Rs. 400–4,000"],
        ["Insurance",                "NOT ELIGIBLE — 0 MR Points",   "—"],
        ["Rent via platforms",       "0 MR Points",                   "Not eligible"],
        ["Utility Bills",            "1 MR Point per Rs. 100",        "No cap"],
        ["EMI Transactions",         "0 MR Points",                   "Not eligible"],
    ]
    story.append(Table(data, colWidths=[5.5*cm, 5.5*cm, 6*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("3. Annual Milestone Benefits"))
    data = [
        ["Annual Spend Milestone",  "Benefit"],
        ["Rs. 1,90,000",            "Complimentary IndiGo economy return ticket OR Rs. 9,000 Taj Voucher"],
        ["Rs. 4,00,000",            "Complimentary IndiGo business class return OR Rs. 18,000 Taj Voucher"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("4. MR Point Redemption Value"))
    data = [
        ["Redemption Option",        "Effective Value per MR Point"],
        ["Taj Hotels Voucher",        "1 MR Point = Rs. 0.50"],
        ["IndiGo Flight Credit",      "1 MR Point = Rs. 0.50"],
        ["Amazon Pay Credits",        "1 MR Point = Rs. 0.25"],
        ["Statement Credit",          "1 MR Point = Rs. 0.25"],
        ["Air India Miles (1:1)",     "1 MR Point = 1 Flying Return Mile"],
    ]
    story.append(Table(data, colWidths=[8*cm, 9*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("5. Transfer Partners"))
    story.append(Body(
        "American Express Membership Rewards Points can be transferred to the following frequent flyer "
        "programmes. Transfers are instant for select partners, or up to 5 business days for others. "
        "Minimum transfer: 1,000 MR Points. Transfers are IRREVERSIBLE."
    ))
    data = [
        ["Partner",                  "Type",    "Transfer Ratio",           "Processing"],
        ["Air India Flying Returns", "Airline",  "1 MR = 1 Flying Return",  "Instant"],
        ["InterMiles",               "Airline",  "1 MR = 1 InterMile",      "3–5 days"],
        ["Etihad Guest",             "Airline",  "1 MR = 1 Etihad Mile",    "3–5 days"],
        ["Taj InnerCircle (Neupass)","Hotel",    "1 MR = 1 Neupass Point",  "3–5 days"],
    ]
    story.append(Table(data, colWidths=[4.5*cm, 2.5*cm, 6*cm, 4*cm], style=table_style()))

    doc.build(story)
    print(f"[OK] Generated: {path}")


# ── Card 5: SBI Cashback Card ────────────────────────────────────────────────
def generate_sbi_cashback():
    path = os.path.join(OUTPUT_DIR, "sbi_cashback.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    story.append(H1("SBI Card Cashback Credit Card"))
    story.append(Body("Cashback Programme Terms and Conditions | Effective Date: 1 January 2025"))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("1. Card Overview"))
    story.append(Body(
        "The SBI Card Cashback Credit Card offers flat cashback on all online and offline transactions. "
        "Unlike points-based cards, the cashback is credited directly to the card statement. "
        "This card is best suited for users who prefer simple, guaranteed cashback over complex reward programmes."
    ))
    story.append(Body("Annual Fee: Rs. 999 + GST"))
    story.append(Body("Fee Waiver: Annual fee waived on annual spends of Rs. 2,00,000 or more."))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("2. Cashback Earn Structure"))
    data = [
        ["Spend Category",           "Cashback Rate",         "Monthly Cap"],
        ["Online Transactions",      "5% cashback",           "Rs. 5,000 per month"],
        ["Offline Transactions",     "1% cashback",           "Rs. 5,000 per month (combined)"],
        ["Dining (online ordering)", "5% cashback",           "Included in online Rs. 5,000 cap"],
        ["Grocery (online)",         "5% cashback",           "Included in online Rs. 5,000 cap"],
        ["Fuel",                     "1% cashback",           "Rs. 100 per statement cycle"],
        ["Utilities",                "1% cashback",           "Included in offline cap"],
        ["Insurance",                "1% cashback",           "Included in offline cap"],
        ["Rent payments",            "NOT ELIGIBLE — 0%",    "—"],
        ["EMI Transactions",         "NOT ELIGIBLE — 0%",    "—"],
        ["Wallet Reloads",           "NOT ELIGIBLE — 0%",    "—"],
    ]
    story.append(Table(data, colWidths=[5.5*cm, 4*cm, 7.5*cm], style=table_style()))
    story.append(Spacer(1, 0.3*cm))

    story.append(H2("3. Cashback Crediting"))
    story.append(Body(
        "Cashback is automatically credited to the card account within 2 working days after the "
        "end of the statement cycle. No redemption request is needed. Cashback credited cannot "
        "be converted to any other form and has no expiry as long as the card is active."
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("4. Important Exclusions"))
    story.append(Body("The following transactions are NOT eligible for cashback:"))
    exclusions = [
        "Rent payments — 0% cashback regardless of platform",
        "EMI conversions — 0% cashback",
        "Cash advance and ATM withdrawals — 0% cashback",
        "Wallet reloads (Paytm, PhonePe, Amazon Pay, etc.) — 0% cashback",
        "Payments to government portals (tax, fees) — 0% cashback",
        "BBPS utility bill payments exceeding Rs. 10,000 — 0% beyond threshold",
        "Education fee payments — 0% cashback",
    ]
    for e in exclusions:
        story.append(BulletItem(e))
    story.append(Spacer(1, 0.2*cm))

    story.append(H2("5. Minimum Transaction for Cashback"))
    story.append(Body(
        "Cashback is applicable on transactions of Rs. 100 or above. Transactions below Rs. 100 "
        "are not eligible for cashback. Partial cashback is not applicable — the full transaction "
        "amount is used for cashback calculation."
    ))

    story.append(H2("6. No Transfer Partners"))
    story.append(Body(
        "SBI Cashback Card does not have any loyalty programme transfer partners. The cashback "
        "is always credited as statement credit and cannot be transferred to any airline or hotel "
        "loyalty programme."
    ))

    doc.build(story)
    print(f"[OK] Generated: {path}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating synthetic credit card PDF documents...")
    generate_axis_atlas()
    generate_hdfc_dcb()
    generate_hdfc_infinia()
    generate_amex_platinum_travel()
    generate_sbi_cashback()
    print(f"\n[DONE] All 5 synthetic PDFs generated in: {OUTPUT_DIR}")
