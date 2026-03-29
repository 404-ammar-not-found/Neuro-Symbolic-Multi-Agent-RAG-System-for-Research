from __future__ import annotations

from typing import Any


def get_api_key() -> str:
    """Return the Gemini API key from env."""

    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment or .env file.")
    return api_key


def lc_deps() -> dict[str, Any]:
    """Lazy-import LangChain dependencies to avoid hard import errors at module import time."""

    try:
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore

        from langchain_community.document_loaders import PyPDFLoader
        from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
        from langchain_community.vectorstores import Chroma
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
    except ImportError as exc:  # pragma: no cover - only when deps missing
        raise ImportError(
            "LangChain dependencies are required. Install langchain, langchain-community, langchain-text-splitters, langchain-core, langchain-google-genai, and pymupdf."
        ) from exc

    return {
        "RecursiveCharacterTextSplitter": RecursiveCharacterTextSplitter,
        "PyPDFLoader": PyPDFLoader,
        "GoogleGenerativeAIEmbeddings": GoogleGenerativeAIEmbeddings,
        "ChatGoogleGenerativeAI": ChatGoogleGenerativeAI,
        "Chroma": Chroma,
        "PromptTemplate": PromptTemplate,
        "StrOutputParser": StrOutputParser,
    }


__all__ = ["get_api_key", "lc_deps"]
