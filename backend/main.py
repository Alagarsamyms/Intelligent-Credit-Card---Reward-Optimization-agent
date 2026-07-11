"""
FastAPI Backend — Main Application
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from monitoring.langsmith_config import setup_langsmith
from backend.api_routes import router

load_dotenv()
setup_langsmith()

app = FastAPI(
    title="Credit Card Rewards Optimization Agent",
    description="Intelligent agent for credit card reward optimization using RAG + LangGraph",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Credit Card Rewards Optimization Agent API",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    from database.db import check_connection
    db_ok = check_connection()
    return {
        "api": "healthy",
        "database": "connected" if db_ok else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
