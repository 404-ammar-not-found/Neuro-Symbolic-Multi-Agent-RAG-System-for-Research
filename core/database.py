"""
ChromaDB database connection and operations.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from core.config import settings


class ChromaDBManager:
    """Manages ChromaDB connections and operations."""
    
    def __init__(self):
        self.client = None
        self.embedder = None
        self.embedding_function = None
        self.collection = None
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            # Create storage directory if it doesn't exist
            storage_path = Path(settings.CHROMA_DB_PATH)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(storage_path),
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding function
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
            
            # Initialize or get collection
            self.collection = self.client.get_or_create_collection(
                name="research_papers",
                embedding_function=self.embedding_function
            )
            
            print("ChromaDB initialized successfully")
            
        except Exception as e:
            print(f"Error initializing ChromaDB: {str(e)}")
            raise
    
    async def add_paper(
        self,
        paper_id: str,
        text_chunks: List[str],
        metadata: Dict[str, Any]
    ) -> None:
        """Add paper chunks to the database."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized")
        
        try:
            # Generate embeddings for all chunks
            embeddings = self.embedding_function(text_chunks)
            
            # Prepare documents and metadatas
            documents = text_chunks
            metadatas = [metadata for _ in text_chunks]
            ids = [f"{paper_id}_{i}" for i in range(len(text_chunks))]
            
            # Add to collection
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
        except Exception as e:
            print(f"Error adding paper to database: {str(e)}")
            raise
    
    async def search_papers(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for papers similar to the query."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_function([query])[0]
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching papers: {str(e)}")
            raise
    
    async def get_paper_metadata(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific paper."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized")
        
        try:
            # Get all chunks for this paper
            results = self.collection.get(
                ids=[f"{paper_id}_{i}" for i in range(10)],  # Try to get first 10 chunks
                include=['metadatas']
            )
            
            # Return metadata from first chunk if available
            if results['metadatas'] and results['metadatas'][0]:
                return results['metadatas'][0]
            
            return None
            
        except Exception as e:
            print(f"Error getting paper metadata: {str(e)}")
            return None
    
    async def delete_paper(self, paper_id: str) -> None:
        """Delete all chunks for a specific paper."""
        if not self.collection:
            raise RuntimeError("ChromaDB not initialized")
        
        try:
            # Get all chunk IDs for this paper
            results = self.collection.get(
                ids=[f"{paper_id}_{i}" for i in range(100)]  # Try to get first 100 chunks
            )
            
            # Delete found chunks
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                
        except Exception as e:
            print(f"Error deleting paper: {str(e)}")
            raise


# Global database manager instance
db_manager = ChromaDBManager()


async def init_chroma_db() -> None:
    """Initialize the ChromaDB database."""
    await db_manager.initialize()


async def get_db_manager() -> ChromaDBManager:
    """Get the database manager instance."""
    if not db_manager.client:
        await db_manager.initialize()
    return db_manager