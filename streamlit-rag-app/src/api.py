from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import os
import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rag_llm import rag_llm_call

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")
MAX_QUERY_LENGTH = int(os.getenv("MAX_QUERY_LENGTH", "2000"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

app = FastAPI(title="CS 2200 AI TA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (per client IP)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, client_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._hits[client_id] = [t for t in self._hits[client_id] if t > cutoff]
        if len(self._hits[client_id]) >= self.max_requests:
            return False
        self._hits[client_id].append(now)
        return True


_limiter = _RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)


class Citation(BaseModel):
    source: str
    details: str


class ContextChunk(BaseModel):
    text: str
    source: str | None = None
    slide_name: str | None = None
    slide_number: int | None = None
    data_source_type: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    context: list[ContextChunk]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _limiter.check(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
        )

    try:
        response, rag_results, slides_used = await asyncio.to_thread(
            rag_llm_call, req.query
        )
    except Exception:
        logger.exception("Pipeline error for query: %s", req.query[:100])
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again later.",
        )

    citations = []
    for slide_str in slides_used:
        parts = slide_str.split(" - ", 1)
        citations.append(Citation(
            source=parts[0].strip(),
            details=f"Slides {parts[1].strip()}" if len(parts) > 1 else "",
        ))

    context = []
    for chunk in rag_results:
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        meta = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
        context.append(ContextChunk(
            text=text,
            source=meta.get("source"),
            slide_name=meta.get("slide_name"),
            slide_number=meta.get("slide_number"),
            data_source_type=meta.get("data source type"),
        ))

    return ChatResponse(answer=response, citations=citations, context=context)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
