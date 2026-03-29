# Neuro-Symbolic Multi-Agent RAG System

## Overview
Streaming PDF ingestion into ChromaDB with Gemini embeddings and an OpenRouter/Gemini Q&A interface, plus a React 3D globe visualizer for graph data.

## Python pipeline (LangChain-based)
- Configure API keys in `.env`: `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
- Install deps (example):
- `pip install langchain langchain-community langchain-text-splitters langchain-core langchain-google-genai chromadb pymupdf python-dotenv`
- Place PDFs in `data/`.
- Run ingestion + interactive QA:
	- `python main.py`
- Vector store persists to `chroma_db/`; QA uses LangChain `RetrievalQA` over Chroma.

## Web visualizer
- Build/serve from `web-visualizer/`:
	- `npm install`
	- `npm run dev`
- Graph data is read from `web-visualizer/public/data/chroma-graph.json` (generated via `python scripts/export_chroma_graph.py`).

## Tests
- Python: `python -m unittest discover -s tests`
- Frontend: `npm test` (Vitest)
