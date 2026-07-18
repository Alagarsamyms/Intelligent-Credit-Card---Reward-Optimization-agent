# Capstone Project: Intelligent Credit Card & Rewards Optimization Agent
## Presentation Deck Outline

This document provides a structured outline for your final Capstone presentation deck. You can copy this content directly into Microsoft PowerPoint or Word to build your slides.

---

### Slide 1: Title Slide
* **Title:** Intelligent Credit Card & Rewards Optimization Agent
* **Subtitle:** An Agentic RAG System for Financial Decision Support
* **Presenter:** [Your Name]
* **Date:** [Date]

### Slide 2: Problem Statement
* **The Complexity of Rewards:** Credit card reward programs are highly complex, with varying reward rates, dynamic transfer ratios, caps, and excluded categories.
* **Information Overload:** Users struggle to manually parse through pages of terms and conditions to determine the best card for a specific transaction or monthly spend.
* **The Need:** A system that can dynamically ingest complex bank documents and provide personalized, mathematically optimized card recommendations based on real-time data.

### Slide 3: Solution Overview
* **Agentic RAG:** An Intelligent Agent powered by Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG).
* **Dual Data Strategy:** Combines unstructured data (raw bank PDFs) with structured database tables (PostgreSQL) for precise calculations.
* **Personalization:** Tailors recommendations to the user's specific card portfolio and reward preferences (Cashback, Points, Miles).

### Slide 4: System Architecture & Workflow
* **Frontend:** Streamlit-based chat interface for seamless user interaction.
* **Orchestration:** LangGraph state machine directing the conversational flow, retrieval, and calculations.
* **Embeddings & Vector Store:** Pinecone vector database for semantic search across ingested credit card PDFs.
* **Structured Data:** Supabase (PostgreSQL) for deterministic entities (User Profiles, Transfer Partners, Reward Rules).
* **LLM Engine:** OpenAI GPT-4o for intent classification, reasoning, and synthesis.

### Slide 5: Technical Stage 1 - Ingestion Pipeline
* **Document Processing:** How raw terms & conditions PDFs are ingested using PyPDFLoader.
* **Chunking Strategy:** Recursive character text splitting to maintain context.
* **Vectorization:** OpenAI Embeddings generating high-dimensional vectors, stored in Pinecone for ultra-fast semantic retrieval.

### Slide 6: Technical Stage 2 - The Core Agent (LangGraph)
* **Intent Classification:** Routing the query (e.g., Single Transaction, Monthly Optimization, Point Transfer).
* **Clarification Node:** Analyzing conversation history to ask missing details (e.g., spend amount, category) without redundant questions.
* **Retrieval & Rule Extraction:** Fetching the correct vector chunks and using LLMs to extract exact reward rates, exclusions, and caps.
* **Deterministic Calculator:** A strict Python mathematical engine that computes the exact INR value of rewards—preventing AI hallucinations.

### Slide 7: Technical Stage 3 - Safety & Guardrails
* **Financial Safety:** The system is explicitly instructed to never give certified financial advice.
* **Rule Validation Tool:** Checks if the retrieved context is sufficient to answer the question. If not, the agent declines to answer rather than inventing data.
* **Explicit Assumptions:** The agent lists all assumptions (e.g., 1 Point = ₹1) clearly in the final output.

### Slide 8: Technical Stage 4 - Human-in-the-Loop (HITL)
* **The Risk of Point Transfers:** Transferring credit card points to airline/hotel partners is usually irreversible.
* **The HITL Implementation:** The LangGraph execution pauses when a transfer is detected.
* **User Consent:** The Streamlit UI displays the assumptions and requires explicit user approval (Confirm/Cancel) before calculating transfer strategies.

### Slide 9: Technical Stage 5 - Observability & Monitoring
* **LangSmith Integration:** Full tracing of every LangGraph node execution.
* **Transparency:** Showcasing the "invisible" work (intent classification, vector search, LLM prompts) behind every single user query.
* **Debugging:** How observability was used to refine the clarification prompts and extraction logic.

### Slide 10: Future Scope & Conclusion
* **Real-time API Integration:** Fetching live currency and dynamic partner transfer ratios.
* **Receipt Parsing:** Allowing users to upload a bill directly for instant card recommendation.
* **Conclusion:** The project successfully demonstrates how Agentic RAG can tame complex, unstructured financial documents into actionable, safe user advice.
