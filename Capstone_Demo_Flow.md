# Capstone Demo Flow (Live Presentation Guide)

This document provides a step-by-step technical script for your live demonstration. Use this guide to seamlessly transition between the Streamlit UI and the backend code, proving your technical depth to the examiners.

---

### Step 1: Show the raw PDFs and the Data Pipeline
**Goal:** Prove that the system handles messy, unstructured banking data and structures it intelligently.
* **UI Action:** Open the `/data/raw_pdfs` folder (if available) or show a snippet of a complex bank PDF on your screen. Point out how difficult it is for humans to parse the dense text.
* **Technical Action (Code):** Open `rag/ingest_pdfs.py`.
* **What to Highlight:** 
    - Highlight the `PyPDFLoader` and `RecursiveCharacterTextSplitter`. Explain that this splits the dense PDFs into semantic chunks.
    - Highlight the Pinecone upsert logic. Explain that you convert these chunks into vector embeddings using OpenAI, allowing the agent to "search" by meaning, not just keywords.
    - Briefly show `database/seed_structured_data.py` to explain that deterministic rules (like exact reward rates) are stored in PostgreSQL (Supabase) for strict mathematical accuracy.

### Step 2: Ask a Simple Query to demonstrate RAG + Calculation
**Goal:** Show the core engine functioning smoothly for a standard transaction.
* **UI Action:** Type in the Streamlit UI: *"Which card should I use for a ₹50,000 flight booking?"*
* **Technical Action (Code):** Open `agents/nodes.py`.
* **What to Highlight:**
    - Highlight the `intent_classification_node`. Show how it identifies the query as a `single_transaction`.
    - Highlight `rule_validation_node`. Explain that before the agent answers, it explicitly checks if the retrieved rules from Pinecone are "Sufficient" to prevent hallucinations.
    - Highlight `calculation_node`. Emphasize that the LLM does **not** do the math. The LLM extracts the rule, but a strict Python function (`_build_calc_inputs`) computes the actual points and ₹ value, ensuring 100% accuracy.

### Step 3: Ask a Multi-Turn Query to show Memory & Clarification
**Goal:** Prove the agent has conversational memory and actively gathers missing requirements.
* **UI Action:** Type in the UI: *"I want to optimize my monthly spends."* (Do not provide spend amounts).
* **UI Result:** The agent should reply asking what your spends are.
* **UI Action:** Reply: *"₹40,000 on groceries and ₹20,000 on dining."* The agent will now provide the calculation.
* **Technical Action (Code):** Open `agents/prompts.py` and `agents/nodes.py`.
* **What to Highlight:**
    - Show `CLARIFICATION_PROMPT` in `prompts.py`. Explain the strict rules that dictate *when* the agent is allowed to ask questions.
    - Show `clarification_node` in `nodes.py`. Point out that the `chat_history` (Memory) is passed into the prompt, which is why the agent remembers the context of the previous turn instead of starting over.

### Step 4: Trigger the Human-in-the-Loop (HITL) Approval
**Goal:** Demonstrate system safety and agentic pausing.
* **UI Action:** Type: *"I have 50,000 points on my Amex. I want to transfer them to Marriott for hotel stays."*
* **UI Result:** The UI will instantly pause and render a Warning/Confirmation button asking for approval before proceeding.
* **Technical Action (Code):** Open `agents/nodes.py` and `app/streamlit_app.py`.
* **What to Highlight:**
    - In `nodes.py`, show `human_approval_node`. Explain that transfers are irreversible, so the agent sets an `awaiting_approval` flag.
    - In `streamlit_app.py`, point to the UI logic that catches this flag and pauses execution, rendering the "Confirm" and "Cancel" buttons. This proves the system is safe for real-world financial applications.

### Step 5: Open LangSmith to prove observability and guardrails
**Goal:** Prove that the agent is doing complex work "under the hood" and that you have full observability.
* **UI Action:** Open your LangSmith dashboard in the browser.
* **What to Highlight:**
    - Click on the trace for your most recent query.
    - Show the execution graph. Point out the invisible steps the user doesn't see (Intent Classification -> Retrieval -> Validation -> Calculation -> Final Answer).
    - Emphasize that this observability allows you to audit the agent, track token usage, and debug hallucinations instantly.
