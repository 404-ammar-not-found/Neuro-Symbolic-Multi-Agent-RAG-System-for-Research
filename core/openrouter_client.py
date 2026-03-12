"""
OpenRouter API client for LLM interactions.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import settings


class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        self.default_model = settings.DEFAULT_LLM_MODEL
        self.fallback_model = settings.FALLBACK_LLM_MODEL
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_DELAY, min=1, max=10),
        reraise=True
    )
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """Generate a completion using OpenRouter API."""
        if not model:
            model = self.default_model
        
        try:
            # Convert async to sync for OpenAI client
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            print(f"Error generating completion with {model}: {str(e)}")
            
            if use_fallback and model != self.fallback_model:
                print(f"Falling back to {self.fallback_model}")
                return await self.generate_completion(
                    messages,
                    model=self.fallback_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_fallback=False
                )
            
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        if model is None:
            # Use local sentence transformer for embeddings to save API costs
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
            return embedder.encode(texts).tolist()
        
        try:
            # Convert async to sync for OpenAI client
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.embeddings.create(
                    model=model,
                    input=texts
                )
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            print(f"Error generating embeddings with {model}: {str(e)}")
            # Fall back to local model
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
            return embedder.encode(texts).tolist()
    
    async def generate_summary(
        self,
        text: str,
        model: Optional[str] = None
    ) -> str:
        """Generate a summary of the given text."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful research assistant. Provide a concise and accurate summary of the given text."
            },
            {
                "role": "user",
                "content": f"Please summarize the following research paper content:\n\n{text}"
            }
        ]
        
        result = await self.generate_completion(
            messages,
            model=model,
            max_tokens=500
        )
        
        return result["content"]
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        model: Optional[str] = None
    ) -> str:
        """Generate an answer to a query using provided context."""
        messages = [
            {
                "role": "system",
                "content": """You are a helpful research assistant. Answer the user's question based on the provided research paper context.
                Be accurate, cite relevant information from the context, and provide detailed explanations.
                If the context doesn't contain enough information to answer the question, say so."""
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nContext: {context}"
            }
        ]
        
        result = await self.generate_completion(
            messages,
            model=model,
            max_tokens=1000
        )
        
        return result["content"]
    
    async def extract_metadata(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured metadata from text."""
        messages = [
            {
                "role": "system",
                "content": """You are a research paper analysis assistant. Extract structured metadata from the given text.
                Return a JSON object with the following fields:
                - title: Paper title
                - authors: List of author names
                - year: Publication year
                - venue: Publication venue/journal/conference
                - abstract: Paper abstract
                - keywords: List of keywords
                - citations: Number of citations (if available)
                
                If information is not available, use null for that field."""
            },
            {
                "role": "user",
                "content": f"Extract metadata from this research paper:\n\n{text}"
            }
        ]
        
        result = await self.generate_completion(
            messages,
            model=model,
            max_tokens=500
        )
        
        try:
            # Try to parse the result as JSON
            import json
            return json.loads(result["content"])
        except:
            # If parsing fails, return a basic structure
            return {
                "title": None,
                "authors": [],
                "year": None,
                "venue": None,
                "abstract": None,
                "keywords": [],
                "citations": None
            }


# Global OpenRouter client instance
openrouter_client = OpenRouterClient()


def get_openrouter_client() -> OpenRouterClient:
    """Get the OpenRouter client instance."""
    return openrouter_client