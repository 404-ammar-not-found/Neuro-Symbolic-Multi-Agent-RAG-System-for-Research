"""PDF parsing utilities: reading and chunking."""

from .text_chunker import TextChunker

try:  # Optional dependency; provide PdfReader when fitz is installed
	from .pdf_reading import PdfReader
	__all__ = ["PdfReader", "TextChunker"]
except ImportError:  # pragma: no cover - only when fitz missing
	PdfReader = None  # type: ignore
	__all__ = ["TextChunker"]
