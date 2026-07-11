"""
Retriever Tool — LangChain Tool wrapper around the RAG retrieval module.
Makes the retriever callable as a LangGraph tool node.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.tools import tool
from rag.retrieval import retrieve, retrieve_by_category


@tool
def retrieve_card_rules(query: str, card_names: str = "", category: str = "") -> str:
    """
    Retrieve relevant credit card reward rules from the vector database.

    Args:
        query: The user's question or the specific rule to look up
        card_names: Comma-separated list of card names to filter (optional)
        category: Spend category to search for (e.g., 'flights', 'dining')

    Returns:
        Formatted string of retrieved chunks with similarity scores
    """
    card_filter = [c.strip() for c in card_names.split(",") if c.strip()] or None

    if category:
        chunks = retrieve_by_category(category, card_filter=card_filter)
    else:
        chunks = retrieve(query, card_filter=card_filter)

    if not chunks:
        return "No relevant card rules found in the database for this query."

    formatted = []
    for i, chunk in enumerate(chunks, 1):
        formatted.append(
            f"[Result {i}] Card: {chunk['card_name']} | "
            f"Similarity: {chunk['similarity']:.2f} | "
            f"Page: {chunk['page_number']}\n"
            f"{chunk['chunk_text']}\n"
        )

    return "\n---\n".join(formatted)
