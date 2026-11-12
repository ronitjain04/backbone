# Course Picker Implementation Plan

**Goal:** Let students choose CS 2110 or CS 2200 and retrieve only that course's material.

**Architecture:** Keep the existing static frontend, Worker proxy and Python API. Send a validated `course` ID with every request; maintain independent backend retrievers and frontend chat state. Load private JSONL corpora from course-specific paths. Preserve legacy CS 2200 configuration and fail closed when a course is unavailable.

**Tech Stack:** Browser JavaScript, Node test runner, FastAPI, pytest.

**User request:** Add a tab for CS 2110 / CS 2200, update the existing website, and create a PR. CS 2110 scope comes from the supplied syllabus; use the three supplied questions as retrieval checks.

## Constraints

- No private textbooks, slides, extracted chunks or indexes in the PR or frontend bundle.
- Preserve branding, existing CS 2200 functionality and current Site audience.
- Unknown or unconfigured courses must not fall back to another course.
- Keep draft questions, messages, errors and pending responses isolated by course.

## Tasks

- [x] Add failing API tests for course isolation, unknown IDs, readiness and unavailable courses; implement a course-indexed retriever registry and course-specific readiness.
- [x] Add failing proxy tests for course validation, request forwarding, readiness, and mismatched response course; implement validated routing with legacy CS 2200 compatibility.
- [x] Add accessible CS 2110 / CS 2200 tabs with course-specific suggestions and independent chat state; test course switching during a pending answer and per-course clearing.
- [x] Document private corpus configuration and reproducible CS 2110 import without publishing data.
- [x] Run backend and frontend suites, build the Worker, check desktop/mobile interaction, review the diff, and open a focused PR against public Backbone main.
- [x] Publish the updated website; update the live backend if workspace authorization and private data delivery permit. Report any remaining deployment limitation precisely.

Validation: 15 backend tests, 14 frontend tests, Worker build and syntax check; real CS 2110 import (1,374 chunks) and all three retrieval checks passed. Browser verified course switching and draft restoration at the default narrow viewport. Independent review found no actionable issues. Pre-existing Starlette/httpx deprecation warning remains. Deployment status is reported separately.
