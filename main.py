"""
Neuro-Symbolic Multi-Agent RAG System for Research Papers
Main entry point for the application.
"""

import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routes import router
from core.config import settings
from core.database import init_chroma_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Neuro-Symbolic RAG System...")
    
    # Initialize ChromaDB
    await init_chroma_db()
    
    yield
    
    logger.info("Shutting down Neuro-Symbolic RAG System...")


app = FastAPI(
    title="Neuro-Symbolic Multi-Agent RAG System",
    description="A system for ingesting, indexing, and querying academic research papers",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Neuro-Symbolic Multi-Agent RAG System",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )