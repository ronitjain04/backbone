# apps/api/app/schemas/course_config.py
# Pydantic v2 models for data/courses/<course_id>/course.yaml

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


# ------------------------
# Policies
# ------------------------

GradedHelpMode = Literal["hints_only", "allow_solutions"]


class Policy(BaseModel):
    graded_help: GradedHelpMode = "hints_only"
    allow_current_homework: bool = False
    require_attempt_for_debugging: bool = True
    fail_closed_on_low_grounding: bool = True


# ------------------------
# Citations
# ------------------------

class CitationFormats(BaseModel):
    # keys match course.yaml citations.formats.*
    slides: str
    textbook: str
    handout: str
    practice_exam: str
    custom: str


class CitationsConfig(BaseModel):
    formats: CitationFormats


# ------------------------
# Parsing / Chunking
# ------------------------

class ChunkingConfig(BaseModel):
    chunk_tokens: int = 320
    overlap_tokens: int = 64


class SlidesParsingConfig(BaseModel):
    lecture_from_filename_regex: str = r"(?i)(lecture|lec)[ _-]?(\d+)"
    chunk_tokens: int = 260
    overlap_tokens: int = 50


class TextbookParsingConfig(BaseModel):
    ocr_enabled: bool = False
    detect_chapters: bool = True
    chunk_tokens: int = 360
    overlap_tokens: int = 70


class HandoutsParsingConfig(BaseModel):
    chunk_tokens: int = 320
    overlap_tokens: int = 64


class PracticeExamsParsingConfig(BaseModel):
    chunk_tokens: int = 320
    overlap_tokens: int = 64


class CustomDefaultsParsingConfig(BaseModel):
    ocr_enabled: bool = False
    chunk_tokens: int = 320
    overlap_tokens: int = 64
    adapter: str = "pdf_text_v1"


class ParsingConfig(BaseModel):
    chunking: ChunkingConfig = ChunkingConfig()
    slides: SlidesParsingConfig = SlidesParsingConfig()
    textbook: TextbookParsingConfig = TextbookParsingConfig()
    handouts: HandoutsParsingConfig = HandoutsParsingConfig()
    practice_exams: PracticeExamsParsingConfig = PracticeExamsParsingConfig()
    custom_defaults: CustomDefaultsParsingConfig = CustomDefaultsParsingConfig()


# ------------------------
# Retrieval
# ------------------------

class RetrievalConfig(BaseModel):
    top_k: int = 12
    use_reranker: bool = True
    rerank_top_n: int = 25
    final_k: int = 6


# ------------------------
# Resources
# ------------------------

class ResourceBase(BaseModel):
    official: bool = True
    expected_path: str


class TextbookResource(BaseModel):
    textbook_id: str
    official: bool = True
    title: Optional[str] = None
    short: Optional[str] = None
    edition: Optional[str] = None
    expected_path: str
    filename_hint_regex: Optional[str] = None


class CustomParsingOverrides(BaseModel):
    chunk_tokens: Optional[int] = None
    overlap_tokens: Optional[int] = None
    ocr_enabled: Optional[bool] = None


class CustomResource(BaseModel):
    resource_id: str
    label: str
    official: bool = True
    expected_path: str
    adapter: str
    citation_format_key: str = "custom"
    parsing_overrides: CustomParsingOverrides = CustomParsingOverrides()


class ResourcesConfig(BaseModel):
    slides: ResourceBase
    textbooks: List[TextbookResource] = Field(default_factory=list)
    handouts: ResourceBase
    practice_exams: ResourceBase
    custom_resources: List[CustomResource] = Field(default_factory=list)


# ------------------------
# Top-level CourseConfig
# ------------------------

class CourseConfig(BaseModel):
    course_id: str
    name: str
    term: Optional[str] = None

    policies: Policy = Policy()
    citations: CitationsConfig
    parsing: ParsingConfig = ParsingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    resources: ResourcesConfig
