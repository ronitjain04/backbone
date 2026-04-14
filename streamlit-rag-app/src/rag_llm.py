from dotenv import load_dotenv
load_dotenv()

import logging
import os
import re

import faiss
import numpy as np
import pickle
import requests
from enum import Enum
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    ISA = "ISA"
    DATAPATH = "DATAPATH"
    CONTROL_PATH = "CONTROL_PATH"
    INTERRUPTS = "INTERRUPTS"
    PERFORMANCE = "PERFORMANCE"
    PIPELINING = "PIPELINING"
    HAZARDS = "HAZARDS"
    SCHEDULING = "SCHEDULING"
    VIRTUAL_MEMORY = "VIRTUAL_MEMORY"
    MEMORY_HIERARCHY = "MEMORY_HIERARCHY"
    PARALLEL_SYSTEMS = "PARALLEL_SYSTEMS"
    NETWORKING = "NETWORKING"
    DISK_SCHEDULING = "DISK_SCHEDULING"
    FILE_SYSTEMS = "FILE_SYSTEMS"

LOCAL_SERVER_OLLAMA = os.getenv('LOCAL_OLLAMA_SERVER', 'http://localhost:11434')
OLLAMA_PUBLIC_KEY = os.getenv('OLLAMA_PUBLIC_KEY')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '120'))
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
OLLAMA_NUM_PREDICT = int(os.getenv('OLLAMA_NUM_PREDICT', '2048'))  # max tokens for longer, tutor-style answers
MIN_SIMILARITY = float(os.getenv('MIN_SIMILARITY', '0.20'))
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '10'))

# ---------------------------------------------------------------------------
# One-time resource loading (runs once at import, not per request)
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data_sources")

logger.info("Loading embedding model...")
_model = SentenceTransformer("all-MiniLM-L6-v2")

logger.info("Loading chunk maps and FAISS indexes from %s ...", _DATA_DIR)
with open(os.path.join(_DATA_DIR, "chunk_map.pkl"), "rb") as _f:
    _chunk_map = pickle.load(_f)

_slides_index = faiss.read_index(os.path.join(_DATA_DIR, "faiss_slides_index.index"))
with open(os.path.join(_DATA_DIR, "chunk_slides_map.pkl"), "rb") as _f:
    _slides_chunk_map = pickle.load(_f)

_book_index = faiss.read_index(os.path.join(_DATA_DIR, "faiss_book_index.index"))
with open(os.path.join(_DATA_DIR, "chunk_book_map.pkl"), "rb") as _f:
    _book_chunk_map = pickle.load(_f)

# Pre-build per-topic FAISS indexes using cosine similarity (inner product
# on L2-normalized vectors) instead of raw L2 distance.  This gives more
# meaningful similarity scores and better ranking.
logger.info("Pre-building per-topic FAISS indexes (cosine similarity)...")
_topic_indexes: dict[str, tuple[faiss.Index, list[dict]]] = {}
for _ds_type in DataSourceType:
    _filtered = [
        entry for entry in _chunk_map.values()
        if "metadata" in entry and entry["metadata"].get("data source type") == _ds_type.name
    ]
    if _filtered:
        _texts = [entry["text"] for entry in _filtered]
        _embeddings = _model.encode(_texts, convert_to_numpy=True, normalize_embeddings=True)
        _idx = faiss.IndexFlatIP(_embeddings.shape[1])
        _idx.add(np.array(_embeddings))
        _topic_indexes[_ds_type.name] = (_idx, _filtered)
        logger.info("  %s: %d chunks", _ds_type.name, len(_filtered))

logger.info("All resources loaded.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rag_llm_call(query: str):
    """Main entry point used by the API.

    To improve robustness, this no longer relies on dspy-based query expansion
    or topic classification (which were brittle with the local model). We:
      1) Use the raw user query for retrieval.
      2) Do a global search over all slides + book, with topic indexes only
         used as a soft hint inside `_search` when we decide to re-enable it.
    """
    logger.info("User query: %s", query)

    # For now, disable topic filtering entirely by passing `data_source=None`.
    rag_results = _search(query, data_source=None, top_k=RAG_TOP_K)
    prompt = _build_prompt(rag_results, query)
    response = _call_ollama(prompt)
    slides_used = _extract_slides_used(rag_results)

    return response, rag_results, slides_used


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _chunk_key(chunk: dict) -> tuple:
    """Create a stable key for de-duplicating chunks."""
    if not isinstance(chunk, dict):
        return ("raw", str(chunk))
    meta = chunk.get("metadata", {}) or {}
    return (
        chunk.get("text", ""),
        meta.get("source"),
        meta.get("slide_name"),
        meta.get("slide_number"),
    )


def _search(query: str, data_source: str | None, top_k: int = RAG_TOP_K) -> list[dict]:
    """Search both globally and (optionally) within a topic, then merge results."""
    query_vec_raw = _model.encode([query])

    # Normalized copy for cosine-similarity (IP) indexes
    query_vec_norm = query_vec_raw.copy()
    faiss.normalize_L2(query_vec_norm)

    # Global search over slides + book
    all_results: list[dict] = []

    D, I = _slides_index.search(np.array(query_vec_raw), k=top_k)
    for j in range(len(I[0])):
        if I[0][j] >= 0:
            all_results.append(_slides_chunk_map[I[0][j]])

    D, I = _book_index.search(np.array(query_vec_raw), k=top_k)
    for j in range(len(I[0])):
        if I[0][j] >= 0:
            all_results.append(_book_chunk_map[I[0][j]])

    # Optional topic-specific search using cosine similarity index.
    topic_results: list[dict] = []
    if data_source and data_source in _topic_indexes:
        index, chunks = _topic_indexes[data_source]
        k = min(top_k, len(chunks))
        D, I = index.search(np.array(query_vec_norm), k=k)
        for j in range(len(I[0])):
            if I[0][j] >= 0 and D[0][j] >= MIN_SIMILARITY:
                topic_results.append(chunks[I[0][j]])
        logger.info(
            "Topic search (%s): %d/%d chunks above threshold %.2f",
            data_source,
            len(topic_results),
            k,
            MIN_SIMILARITY,
        )

    # If topic search gave us nothing reliable, just use the global results.
    if not topic_results:
        return all_results

    # Merge topic results (first) with global results, de-duplicated.
    merged: list[dict] = []
    seen: set[tuple] = set()
    for chunk in topic_results + all_results:
        key = _chunk_key(chunk)
        if key in seen:
            continue
        seen.add(key)
        merged.append(chunk)
        if len(merged) >= top_k * 2:
            break

    return merged


def _format_context(rag_results: list[dict]) -> str:
    """Turn raw result dicts into clean, numbered text the LLM can read."""
    parts = []
    for i, chunk in enumerate(rag_results, 1):
        if not isinstance(chunk, dict):
            parts.append(f"[{i}] {chunk}")
            continue

        text = chunk.get("text", "").strip()
        if not text:
            continue

        meta = chunk.get("metadata", {})
        source = meta.get("source", "")

        if source == "slides":
            name = meta.get("slide_name", "Unknown slides")
            num = meta.get("slide_number", "?")
            label = f"[{i}] (Slides: {name}, Slide #{num})"
        elif source in ("book", "text"):
            label = f"[{i}] (Textbook)"
        else:
            label = f"[{i}]"

        parts.append(f"{label}\n{text}")

    return "\n\n".join(parts)


def _has_enough_overlap(query: str, rag_results: list[dict]) -> bool:
    """Heuristic: does the retrieved context mention key words from the query?"""
    keywords = [
        w.lower()
        for w in re.findall(r"\w+", query)
        if len(w) > 3
    ]
    if not keywords:
        return True

    corpus_parts: list[str] = []
    for chunk in rag_results:
        if isinstance(chunk, dict):
            corpus_parts.append(chunk.get("text", ""))
        else:
            corpus_parts.append(str(chunk))
    corpus = " ".join(corpus_parts).lower()

    hits = sum(1 for w in keywords if w in corpus)
    required = max(2, len(keywords) // 4)
    return hits >= required


def _build_prompt(rag_context: list[dict], query: str) -> str:
    formatted = _format_context(rag_context)

    prompt_intro = (
        "You are a patient, encouraging tutor for CS 2200 (Systems & Networks) at Georgia Tech. "
        "Your goal is to help the student understand the material, not just state facts. "
        "Use ONLY the provided context below—be accurate and cite slide names and slide numbers when you use them. "
        "Explain thoroughly: give a clear overview first, then go into detail. Use step-by-step or bullet points for lists (e.g. instruction formats, stages, or options). "
        "Use **bold** for key terms and important ideas. "
        "Where it helps, use a tutor tone: e.g. \"A key point here is...\", \"Think of it this way...\", \"To tie it together...\", or a short recap at the end. "
        "Be a bit verbose when it aids clarity; avoid one-line answers. "
        "If the context does not contain enough to fully answer, say what you can from the materials and note what is missing—do not invent content. "
    )

    if not _has_enough_overlap(query, rag_context):
        prompt_intro += (
            "The retrieved context may not actually match the question. "
            "If you cannot clearly find the answer in the context, explicitly say "
            "\"the provided course materials do not contain enough information to "
            "answer this question\" and do not invent an answer from outside "
            "knowledge.\n\n"
        )
    else:
        prompt_intro += "\n\n"

    return (
        f"{prompt_intro}"
        f"--- Context ---\n{formatted}\n\n"
        f"--- Student Question ---\n{query}\n\n"
        "--- Answer ---\n"
    )


def _call_ollama(prompt: str, model: str | None = None) -> str:
    if model is None:
        model = OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": OLLAMA_NUM_PREDICT},
    }
    response = requests.post(
        f"{LOCAL_SERVER_OLLAMA}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["response"]


def _extract_slides_used(rag_results: list[dict]) -> list[str]:
    slides_accumulated: dict[str, list[int]] = {}
    for result in rag_results:
        meta = result.get("metadata") if isinstance(result, dict) else None
        if not meta or meta.get("source") != "slides":
            continue
        slide_name = meta["slide_name"]
        slides_accumulated.setdefault(slide_name, []).append(meta["slide_number"])

    return [
        f"{name} - {', '.join(map(str, sorted(numbers)))}"
        for name, numbers in slides_accumulated.items()
    ]


if __name__ == "__main__":
    rag_llm_call(query="What is LC-2200 Architecture")
