# scripts/generate_manifest_textbook_only.py
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import re
import yaml

# Import your Pydantic schemas
# Adjust import paths to your project layout
from apps.api.app.schemas.course_config import CourseConfig
from apps.api.app.schemas.manifest_config import ManifestConfig

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing YAML: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
    
def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
        
def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def list_files(dir_path: Path) -> list[Path]:
    if not dir_path.exists():
        return []
    return [p for p in dir_path.rglob("*") if p.is_file()]


def pick_textbook_files(files: list[Path], filename_hint_regex: str | None) -> list[Path]:
    if not files:
        return []
    if not filename_hint_regex:
        return files
    hint = re.compile(filename_hint_regex)
    matched = [f for f in files if hint.search(f.name)]
    return matched if matched else files  # fallback if no match

def manifest_textbook(course_cfg: CourseConfig, version_dir: Path):

    # 2) Scan textbook folder(s)
    documents: list[dict] = []

    for tb in course_cfg.resources.textbooks:
        tb_dir = version_dir / tb.expected_path  # expected_path is like "raw/textbook/"
        files = pick_textbook_files(list_files(tb_dir), tb.filename_hint_regex)

        # Resolve ingestion settings from course.yaml parsing.textbook
        ingest_adapter = course_cfg.parsing.custom_defaults.adapter  # fallback
        # In your course.yaml you set custom_defaults.adapter=pdf_text_v1
        # For textbook, we still want pdf_text_v1 unless you decide otherwise
        ingest_adapter = "pdf_text_v1"

        chunk_tokens = course_cfg.parsing.textbook.chunk_tokens
        overlap_tokens = course_cfg.parsing.textbook.overlap_tokens

        for fp in files:
            # doc_id scheme: stable per textbook_id (not per filename) is usually best
            doc_id = f"doc_textbook_{slugify(fp.name)}"
            title = fp.name

            documents.append(
                {
                    "doc_id": doc_id,
                    "doc_type": "textbook",
                    "title": title,
                    "raw_path": str(fp.relative_to(version_dir)),
                    "sha256": sha256_file(fp),
                    "ingestion": {
                        "adapter": ingest_adapter,
                        "chunk_tokens": chunk_tokens,
                        "overlap_tokens": overlap_tokens,
                        "ocr_enabled": course_cfg.parsing.textbook.ocr_enabled,
                        "detect_chapters": course_cfg.parsing.textbook.detect_chapters,
                    },
                    # inferred can be omitted for textbook; your schema allows inferred=None
                }
            )
        return len(documents), documents

    # manifest_dict = {
    #     "course_id": course_id,
    #     "version_id": version_id,
    #     "created_at": created_at,
    #     "build": {
    #         "ingestion_pipeline": "ingest_v1",
    #         "embedding_model": "BAAI/bge-small-en-v1.5",
    #         "reranker_model": "BAAI/bge-reranker-base",
    #         "defaults": {
    #             "chunk_tokens": course_cfg.parsing.chunking.chunk_tokens,
    #             "overlap_tokens": course_cfg.parsing.chunking.overlap_tokens,
    #         },
    #         "status": "pending",
    #         "num_documents": len(documents),
    #     },
    #     "documents": documents,
    # }

    # # 3) Validate manifest against your ManifestConfig
    # manifest_obj = ManifestConfig.model_validate(manifest_dict)

    # # 4) Write it out
    # out_path = version_dir / "manifest.yaml"
    # write_yaml(out_path, manifest_obj.model_dump(exclude_none=True))
    # print(f"Wrote manifest: {out_path}")

def infer_lecture_num(filename: str, lecture_regex: re.Pattern) -> int | None:
    m = lecture_regex.search(filename)
    if not m:
        return None
    # your regex: (?i)(lecture|lec)[ _-]?(\\d+)
    # group(2) is the number
    try:
        return int(m.group(2))
    except Exception:
        return None

def manifest_slides(course_cfg: CourseConfig, version_dir: Path):

    # 1) Locate slides folder from course.yaml expected_path
    slides_rel = course_cfg.resources.slides.expected_path  # e.g. "raw/slides/"
    slides_dir = version_dir / slides_rel

    lecture_regex = re.compile(course_cfg.parsing.slides.lecture_from_filename_regex)

    documents: list[dict] = []

    # 2) Build doc entries for each slide PDF
    for fp in sorted(list_files(slides_dir)):
        stem = fp.stem
        lecture = infer_lecture_num(fp.name, lecture_regex)

        # Stable doc_id suggestion:
        # - If lecture inferred: doc_slides_lec01, doc_slides_lec02, ...
        # - Else fallback to filename slug
        if lecture is not None:
            doc_id = f"doc_slides_lec{lecture:02d}"
            title = f"Lecture {lecture:02d}"
        else:
            doc_id = f"doc_slides_{slugify(stem)}"
            title = stem

        documents.append(
            {
                "doc_id": doc_id,
                "doc_type": "slides",
                "title": title,
                "raw_path": str(fp.relative_to(version_dir)),
                "sha256": sha256_file(fp),
                "ingestion": {
                    # choose a convention; slides are naturally page-based
                    "adapter": "pdf_pages_v1",
                    "chunk_tokens": course_cfg.parsing.slides.chunk_tokens,
                    "overlap_tokens": course_cfg.parsing.slides.overlap_tokens,
                },
                "inferred": {"lecture": lecture} if lecture is not None else None,
            }
        )

    # Remove inferred=None to keep YAML clean
    for d in documents:
        if d.get("inferred") is None:
            d.pop("inferred", None)
    
    return len(documents), documents

    # 4) Build manifest
    # manifest_dict = {
    #     "course_id": course_id,
    #     "version_id": version_id,
    #     "created_at": created_at,
    #     "build": {
    #         "ingestion_pipeline": "ingest_v1",
    #         "embedding_model": "BAAI/bge-small-en-v1.5",
    #         "reranker_model": "BAAI/bge-reranker-base",
    #         "defaults": {
    #             "chunk_tokens": course_cfg.parsing.chunking.chunk_tokens,
    #             "overlap_tokens": course_cfg.parsing.chunking.overlap_tokens,
    #         },
    #         "status": "pending",
    #         "num_documents": len(documents),
    #     },
    #     "documents": documents,
    # }

    # 5) Validate against your schema
    # manifest_obj = ManifestConfig.model_validate(manifest_dict)

    # # 6) Write it out
    # out_path = version_dir / "manifest.yaml"
    # write_yaml(out_path, manifest_obj.model_dump(exclude_none=True))
    # print(f"Wrote manifest: {out_path}")

def generate_manifest(course_id: str, version_id: str):
    
    data_root = Path("data")
    course_dir = data_root / "courses" / course_id
    version_dir = course_dir / "versions" / version_id

    # 1) Load + validate course.yaml
    course_cfg = CourseConfig.model_validate(read_yaml(course_dir / "course.yaml"))
    
    created_at = datetime.now(timezone.utc).isoformat()
    
    num_textbooks, textbook_documents = manifest_textbook(course_cfg=course_cfg, version_dir=version_dir)
    num_slides, slide_documents = manifest_slides(course_cfg=course_cfg, version_dir=version_dir)
    
    num_documents = num_textbooks + num_slides
    documents = textbook_documents + slide_documents
    
    manifest_dict = {
        "course_id": course_id,
        "version_id": version_id,
        "created_at": created_at,
        "build": {
            "ingestion_pipeline": "ingest_v1",
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "reranker_model": "BAAI/bge-reranker-base",
            "defaults": {
                "chunk_tokens": course_cfg.parsing.chunking.chunk_tokens,
                "overlap_tokens": course_cfg.parsing.chunking.overlap_tokens,
            },
            "status": "pending",
            "num_documents": num_documents,
        },
        "documents": documents,
    }
    
    # 5) Validate against your schema
    manifest_obj = ManifestConfig.model_validate(manifest_dict)

    # 6) Write it out
    out_path = version_dir / "manifest.yaml"
    write_yaml(out_path, manifest_obj.model_dump(exclude_none=True))
    print(f"Wrote manifest: {out_path}")

def main(course_id: str, version_id: str) -> None:
    # manifest_textbook(course_id=course_id, version_id=version_id)
    generate_manifest(course_id=course_id, version_id=version_id)


if __name__ == "__main__":
    main(course_id="cs2200", version_id="v0001")