# Neuro-Symbolic Multi-Agent RAG System for Research

A system that searches arXiv for research papers on any topic, stores them in a vector database (ChromaDB), and lets you semantically query the knowledge base — all through a React frontend.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

---

## 1. Clone & set up the backend

```bash
cd /path/to/Neuro-Symbolic-Multi-Agent-RAG-System-for-Research

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

## 2. Configure environment variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_key_here

# Optional — defaults are fine for local dev
API_HOST=0.0.0.0
API_PORT=8000
CHROMA_DB_PATH=./storage/chromadb
EMBEDDING_MODEL=all-MiniLM-L6-v2
DEFAULT_LLM_MODEL=meta-llama/llama-3-8b-instruct:free
```

> The `OPENROUTER_API_KEY` is used to generate diverse search queries. If it's missing or fails, the system falls back to built-in queries automatically — so the app still works without it.

---

## 3. Run the backend

```bash
# From the project root, with the venv active
python main.py
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

---

## 4. Run the frontend

Open a **second terminal**:

```bash
cd frontend
npm install        # first time only
npm run dev
```

The UI will be available at `http://localhost:5173`.

---

## Usage

1. **Research tab** — type a topic (e.g. "Vision transformers") and click Run. The agent searches arXiv, deduplicates papers, and stores them in ChromaDB.
2. **Query tab** — ask a natural-language question. The system does semantic search over everything stored so far.
3. **Stats panel** — shows total chunks stored in the knowledge base.

---

## Project structure

```
.
├── main.py                  # FastAPI entry point
├── requirements.txt
├── .env                     # your secrets (not committed)
├── api/
│   └── routes.py            # /research, /query, /stats endpoints
├── agents/
│   └── research_agent.py    # orchestrates query gen → scrape → store
├── core/
│   ├── config.py            # settings loaded from .env
│   ├── database.py          # ChromaDB wrapper
│   └── openrouter_client.py # LLM client
├── ingestion/
│   ├── arxiv_scraper.py     # arXiv API search + PDF download
│   └── pdf_parser.py        # PDF → text chunks
├── storage/
│   └── chromadb/            # vector DB files (auto-created)
└── frontend/                # React + Vite + TypeScript UI
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Failed to fetch` in the UI | The backend is not running. Start it with `python main.py`. |
| `CORS error` in browser console | Make sure you're accessing the frontend at `localhost:5173`, not a different port. |
| `ModuleNotFoundError` on startup | Run `pip install -r requirements.txt` with the venv active. |
| ChromaDB errors on first run | The `storage/chromadb/` directory is auto-created — ensure the process has write access. |
| LLM query generation fails | Check your `OPENROUTER_API_KEY`. The system falls back to simple queries automatically. |
