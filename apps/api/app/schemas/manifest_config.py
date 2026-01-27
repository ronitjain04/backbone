from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional

DocType = Literal["slides", "textbook", "handout", "practice_exam", "custom", "code"]

class IngestionConfig(BaseModel):
    adapter: str
    
    #chunking
    chunk_tokens: int
    overlap_tokens: int
    
    #optional flags
    ocr_enabled: Optional[bool] = None
    detect_chapters: Optional[bool] = None
    detect_questions: Optional[bool] = None
    language: Optional[str] = None
    
    #optional config bag from future adapter-specific knobs
    extra: Dict[str, Any] = Field(default_factory=dict)

class InferredConfig(BaseModel):
    lecture: Optional[int] = None
    exam: Optional[int] = None
    question_set: Optional[str] = None
    unit: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class DocumentConfig(BaseModel):
    doc_id: str
    doc_type: DocType
    title: str
    raw_path: str
    sha256: str
    ingestion: IngestionConfig
    inferred: Optional[InferredConfig] = None
    
    # optional for custom resources
    resource_id: Optional[str] = None
    resource_label: Optional[str] = None
    textbook_id: Optional[str] = None
    

class BuildDefaults(BaseModel):
    chunk_tokens: int
    overlap_tokens: int

class BuildConfig(BaseModel):
    ingestion_pipeline: str
    embedding_model: str
    reranker_model: str
    defaults: BuildDefaults
    
    status: Optional[Literal["pending", "ingested", "indexed", "failed"]] = None
    finished_at: Optional[str] = None
    
    num_documents: Optional[int] = None
    num_chunks: Optional[int] = None
    
    extra: Dict[str, Any] = Field(default_factory=dict)
        

class ManifestConfig(BaseModel):
    course_id: str
    version_id: str
    created_at: str
    
    build: Optional[BuildConfig] = None
    
    documents: List[DocumentConfig] = Field(default_factory=list)
    
    
    