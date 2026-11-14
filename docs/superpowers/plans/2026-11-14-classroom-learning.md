# Classroom Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Demonstrate mistake-linked visual help, independent transfer checks, live classroom evidence, and recorded replay.

**Architecture:** Add additive PostgreSQL migrations and server-owned outcomes/presence to existing practice sessions. Use a shared event reducer and replay component, a reviewed memory visual, and protected five-second teacher polling. Evaluate against isolated PostgreSQL and separate deterministic/load measurements from model evidence.

**Tech Stack:** FastAPI, psycopg, PostgreSQL 17/Neon, Groq, plain JavaScript, existing Vercel hosting.

**Spec:** docs/superpowers/specs/2026-11-14-classroom-learning-design.md

## Global Constraints
- Retain anonymous saved student sessions, one demo classroom, and protected teacher access using the existing owner credential.
- Poll the teacher view every five seconds; heartbeat approximately every 15 seconds while visible.
- Last signal under 45 seconds is active; 45–120 seconds is stale; over 120 seconds or all known tabs explicitly left means disconnected/closed.
- Never rerun retrieval or a model during replay.
- Keep public production on the merged baseline until a new release is authorized.
- Do not expose course corpus excerpts, secrets, or student data in the public evaluation report.

## Review Focus
- Concurrent hint/check completion must not erase assistance: task 1 tests overlapping reservation/completion.
- Delayed tab leave must not override a newer heartbeat: task 2 tests monotonic sequence rejection.
- Historical sessions must retain usable exercises: tasks 1/3 test old completion classification and metadata compatibility.
- Evidence and student text may contain markup: task 4 tests renderer uses text nodes, plus browser inspection.
- Hidden tabs and polling failures must not silently imply live classroom data: task 4 tests presence labels and error state.

### Task 1: Outcomes and migration
**Files:** practice/migrations/002_classroom.sql; practice/store.py; practice/learning.py; tests/test_practice_learning.py (paths under website/backend).
**Interfaces:** `outcome(assisted: bool) -> str`; Store snapshots expose outcome and assistance; begin/finish action retains idempotency. Follow-ups require completed parent in ensure_progress.
- [x] Write tests for helped versus independent parent/follow-up, immutable first outcome, historical completed rows, follow-up gate, migration rerun, concurrent assistance reservation.
- [x] Run `TEST_DATABASE_URL=... python -m pytest website/backend/tests/test_practice_learning.py -q`; expect missing behavior failure.
- [x] Implement migration ledger, additive columns, assistance provenance and learning events; preserve current immutable bank versions.
- [x] Run learning and existing store/API tests; expect PASS; commit.

### Task 2: Visual and classroom API
**Files:** practice/visual.py; practice/classroom.py; practice/store.py; practice/routes.py; tests/test_practice_classroom.py.
**Interfaces:** Store.visual(token,exercise_id,key,stage,address_bits,bits_per_location); Store.presence(token,tab_id,seq,connected); Store.classroom() compact evidence summaries; authorized classroom detail/events. Visual response contains reviewed stages, refs, persisted state and supported evidence.
- [x] Write tests for nonleaking visual stages, source grounding, unsupported diagnosis clarification, duplicate keys, invalid stages, presence multi-tab/order/thresholds, dashboard evidence and owner isolation.
- [x] Run classroom tests; expect failure for missing API.
- [x] Implement bounded visual state and idempotent assistance events, per-tab presence, grouped dashboard and protected detail routes. Use explicit presentation metadata keyed by stable exercise IDs so historical exercise definitions remain unchanged.
- [x] Run classroom + learning + API tests; expect PASS; commit.

### Task 3: Student visual and replay
**Files:** website/site/practice.html; practice.mjs; learning.mjs; replay.mjs; memory-visual.mjs; styles.css; tests/learning.test.mjs.
**Interfaces:** `reduceEvents(events,index)` returns exercise states and milestones; `mountReplay(root,events)` returns cleanup; `mountMemoryVisual(root,{exercise,progress,request,onState})`; outcomes named exactly as server.
- [x] Write reducer tests for mistake/hint/correction/independent follow-up, old events, seek before completion and visual restoration; test bounded visual arithmetic and no current answer substitution.
- [x] Run `node --test website/site/tests/learning.test.mjs`; expect missing module failure.
- [x] Implement shared components, play/pause/seek/speed/significant moments, student outcome labels, visual help, heartbeat/reconnect and persisted visual state. Use text nodes for submitted evidence and accessible control labels.
- [x] Run frontend tests/build; expect PASS; commit.

### Task 4: Teacher workspace
**Files:** website/site/teacher.html; teacher.mjs; classroom-view.mjs; assets.mjs; styles.css; tests/classroom.test.mjs.
**Interfaces:** five-second refresh of /classroom and on-demand /classroom/{id}/detail and /events with existing X-Practice-Owner. Shared replay module from task 3.
- [x] Write tests for exact group keys, uncertainty, stale labels, hostile evidence rendering contract and failure status copy.
- [x] Run classroom tests; expect missing module failure.
- [x] Implement protected login, live rows/groups, detail evidence, jump to replay, last refresh/error, hidden-tab polling pause, mobile layout and static build inclusion.
- [x] Run all frontend tests/build; expect PASS; commit.

### Task 5: Reliability evaluation and review delivery
**Files:** backend/tests/test_practice_classroom_load.py; backend/tools/evaluate_classroom.py; docs/verification/2026-11-14-classroom-learning.md; README.md.
**Interfaces:** executable report produces JSON with sample counts, endpoint latencies p50/p95/max/errors, duplicate/reconnect invariants and citation checks. Controlled model boundary explicitly identified.
- [x] Write 30-student integration test with 60 action flow, concurrent duplicates, reconnects and teacher reads; write accuracy fixtures spanning all five requested input categories and leakage.
- [x] Run new tests, observe failure if invariants missing, implement only required fixes, and run full backend/frontend suites with real isolated PostgreSQL.
- [x] Run latency report and citation/source validation; document measured sample and limitations. Verify isolated Neon migration, hosted review deployment, desktop/mobile visual/dashboard/replay.
- [ ] Commit, request fresh whole-branch review, fix material findings with regression tests, push review PR, inspect CI to completion. Public production remains unchanged.
