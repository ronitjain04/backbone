# CS 2200 AI TA (Backbone) — Quick Start

## Run the app

1. **Prereqs:** Python 3.10+, [Ollama](https://ollama.ai) running with a model (e.g. `mistral`)
2. **Install:** `pip install -r requirements.txt`
3. **Configure:** Copy `.env.example` to `.env` and edit if needed
4. **Start:** From `src/` run `uvicorn api:app --reload`
5. **Open:** http://localhost:8000

## What this app does

- User asks a question about CS 2200 (ISA, datapath, pipelining, etc.)
- Backend retrieves relevant chunks from slides + textbook (FAISS search)
- Ollama generates an answer using that context
- Frontend shows the answer plus slide citations

## Main files

| File | Role |
|------|------|
| `api.py` | FastAPI server; `POST /api/chat` handles questions |
| `rag_llm.py` | RAG pipeline: search → build prompt → call Ollama |
| `static/` | Frontend (index.html, app.js, styles.css) |

## Data

Expects `data_sources/` at `../../data_sources` from `src/` with:
- `faiss_slides_index.index`, `chunk_slides_map.pkl`
- `faiss_book_index.index`, `chunk_book_map.pkl`
- `chunk_map.pkl`

## Recent backend changes (summary)

- Models and indexes load once at startup (faster)
- Cleaner prompt formatting and tutor-style instructions
- CORS, rate limiting, input validation, error sanitization
- Config via env vars (OLLAMA_MODEL, RAG_TOP_K, etc.)
