"""
PDF processing utilities for research papers.
"""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.config import settings


class PDFParser:
    """Handles PDF text extraction and processing."""
    
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page in doc:
                text += page.get_text() + "\n"
            
            doc.close()
            return text
            
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""
    
    async def extract_text_with_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and basic metadata from PDF."""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract basic metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "page_count": len(doc)
            }
            
            # Extract text
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            
            doc.close()
            
            return {
                "text": text,
                "metadata": metadata,
                "file_path": pdf_path
            }
            
        except Exception as e:
            print(f"Error extracting text and metadata from {pdf_path}: {str(e)}")
            return {
                "text": "",
                "metadata": {},
                "file_path": pdf_path
            }
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []
        
        # Split into sentences first for better chunking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length <= self.chunk_size:
                current_chunk += sentence + " "
                current_length += sentence_length
            else:
                # Add current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_sentences = sentences[max(0, len(chunks) - 2):len(chunks)]
                overlap_text = " ".join(overlap_sentences)
                
                current_chunk = overlap_text + " " + sentence
                current_length = len(current_chunk.split())
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF file and return structured data."""
        # Extract text and metadata
        result = await self.extract_text_with_metadata(pdf_path)
        
        # Create chunks
        chunks = self.chunk_text(result["text"])
        
        # Prepare structured result
        paper_data = {
            "file_path": pdf_path,
            "original_text": result["text"],
            "chunks": chunks,
            "metadata": result["metadata"],
            "chunk_count": len(chunks)
        }
        
        return paper_data
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """Validate if a file is a valid PDF."""
        try:
            if not Path(pdf_path).exists():
                return False
            
            if Path(pdf_path).stat().st_size > settings.MAX_PDF_SIZE:
                print(f"PDF too large: {pdf_path}")
                return False
            
            doc = fitz.open(pdf_path)
            is_valid = len(doc) > 0
            doc.close()
            
            return is_valid
            
        except Exception:
            return False