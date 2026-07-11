"""
LangSmith Monitoring Configuration
Sets up LangSmith tracing for all LangGraph and LangChain calls.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def setup_langsmith():
    """
    Configure LangSmith tracing environment variables.
    Call this once at application startup before any LangChain imports.
    """
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "credit-card-rewards-agent")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "true")

    if not api_key:
        print("[WARN]  LANGCHAIN_API_KEY not set. LangSmith tracing is DISABLED.")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = tracing
    os.environ["LANGCHAIN_ENDPOINT"] = os.getenv(
        "LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"
    )
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project

    print(f"[OK] LangSmith tracing enabled → Project: {project}")
    return True


def get_run_url(run_id: str) -> str:
    """Get the LangSmith URL for a specific run."""
    project = os.getenv("LANGCHAIN_PROJECT", "credit-card-rewards-agent")
    return f"https://smith.langchain.com/o/default/projects/{project}/runs/{run_id}"
