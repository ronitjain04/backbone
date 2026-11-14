# Guided Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Ship the approved six-stage course-grounded practice demo.
**Architecture:** Add focused practice modules to the current FastAPI application, persist in PostgreSQL, and bundle an accessible practice workspace alongside chat. Reuse the private CS2110 retriever and Groq model boundary.
**Tech Stack:** Python/FastAPI, psycopg 3, PostgreSQL, JavaScript, existing Markdown renderer and Vercel.
**Spec:** docs/superpowers/specs/2026-11-14-guided-practice-design.md

## Global Constraints
- 18 original CS2110 exercises; private corpus excerpts never committed.
- PostgreSQL persistence, no SQLite substitute; opaque cookie identity and protected classroom replay.
- Unsupported input is uncertain, never silently incorrect. Never execute arbitrary student code.
- Work on codex/guided-practice; keep existing chat working; push a reviewable PR without merging.

## Review Focus
- Duplicate requests and concurrent tabs must not advance hints or overwrite work.
- Forged source IDs or invented student quotations must not produce a misconception.
- A wrong final answer without reasoning must not imply an invented first error.
- Browser refresh and model failure must retain attempted work and event history.
- Public assets and exercise responses must not leak answer keys or private corpora.

### Task 1: Exercise bank
**Files:** backend/practice/bank.py, bank.json, tools/validate_practice_sources.py, tests/test_practice_bank.py (under website).
**Interfaces:** load_bank() -> dict keyed by exercise ID; public_exercise(record) -> safe prompt metadata; references hold source/details/fingerprint.
- [x] Write tests for 18 complete exercises, hidden answers and source fingerprint validation; watch fail.
- [x] Author 18 exercises and follow-ups; inspect actual supporting textbook/slides; bind private-corpus fingerprints.
- [x] Run bank tests and private validation; commit.

### Task 2: Persistence
**Files:** backend/practice/store.py, migrations/001_practice.sql, tests/test_practice_store.py; requirements and CI PostgreSQL service.
**Interfaces:** Store(dsn), migrate(), seed(bank), create_student(), snapshot(token), save_draft(token, exercise_id, answer, work, revision), begin_action(...), finish_action(...), events(token).
- [x] Write real PostgreSQL integration tests for identity, restore, revisions, concurrent event order, idempotency and delete; watch fail.
- [x] Add migration and transactional store with per-session locking, digest tokens and pinned exercise versions.
- [x] Run integration tests against real local PostgreSQL; commit.

### Task 3: Workspace and API
**Files:** backend/practice/routes.py, backend/site.py, backend/app.py; site/practice.mjs, site/index.html, site/styles.css, site/assets.mjs; tests/test_practice_api.py and site/tests/practice.test.mjs.
**Interfaces:** /api/practice/start, /state, /draft, /check, /hint, /events, /delete and protected /classroom; same-origin JSON writes with cookie auth.
- [x] Write API isolation/origin/body-limit tests and browser refresh/draft/failure tests; watch fail.
- [x] Add safe practice workspace, cookies, revision handling, replay and protected owner view; initially check/hint return unavailable.
- [x] Run API/browser tests and builds; commit.

### Task 4: Answer checking
**Files:** backend/practice/checking.py, lc3.py, assessment.py; backend/inference.py; tests/test_practice_checking.py.
**Interfaces:** check(exercise, answer, work) -> structured verdict; assess(exercise, answer, work, chunks, model) -> rubric verdict with evidence.
- [x] Test alternative numeric expressions, units, LC3 bounds, explanation rubrics and unsupported input; watch fail.
- [x] Implement bounded parsing/interpreter and validated structured model rubric; wire checks with durable actions.
- [x] Run checker and API tests; commit.

### Task 5: Misconceptions
**Files:** backend/practice/assessment.py, checking.py; tests/test_practice_assessment.py.
**Interfaces:** feedback.misconception contains label, exact evidence, criterion, source IDs, or null; clarification is explicit.
- [x] Test first supported ordered error, wrong-answer-only uncertainty, invalid quotations/citations and alternative explanation acceptance; watch fail.
- [x] Add conservative evidence validation and criterion-level reasoning assessment.
- [x] Run assessment tests; commit.

### Task 6: Progressive hints and final verification
**Files:** backend/practice/hints.py, routes.py; tests/test_practice_hints.py; website/README.md, docs verification ledger.
**Interfaces:** hint(exercise, level, attempts, retriever) -> text, verified sources, level; maximum level 3.
- [x] Test citation fingerprint checks, prior attempt adaptation, no final-answer disclosure, idempotent progression and unavailable retrieval; watch fail.
- [x] Implement curated progressive hint retrieval; complete follow-up navigation, replay UI and deployment instructions.
- [x] Run backend/frontend suites, actual PostgreSQL tests, private source validation and builds; visually verify desktop/mobile and refresh.
- [x] Obtain fresh code review, fix substantive issues, push branch and open/attach PR. Report any hosted database dependency explicitly.
