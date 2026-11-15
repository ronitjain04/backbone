# CI Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Strengthen release verification and remove verified maintenance debt without changing hosting or learning behavior.

**Architecture:** Keep the existing Vercel/FastAPI stack and live Sites compatibility. Batch classroom projections; consolidate the local launcher; add deterministic full-stack browser/migration/quality gates; stage and verify production candidates before promotion. Separate live provider monitoring from deployments.

**Tech Stack:** Python 3.12, FastAPI/psycopg/PostgreSQL 17, Node 24, Chromium/Playwright, GitHub Actions, Vercel CLI.

**Spec:** docs/superpowers/specs/2026-11-14-ci-maintenance-design.md

## Global Constraints
- Preserve the still-active Sites Worker build and compatibility tests.
- Create a separate stacked PR against codex/classroom-learning; do not merge or publish.
- Pull requests receive no deployment/model/database secrets; browser data is synthetic.
- Do not automatically apply destructive database rollback.
- Preserve ownership, source verification, idempotency and outcome contracts.

## Review Focus
- Older bank versions and missing optional progress must retain teacher row behavior (task 1).
- Expired reservations must settle under deterministic locks without deadlocking simultaneous students (task 1).
- Browser fixtures and fake authentication must never enter deployed production functions (task 3).
- A candidate failure, stale main, malformed URL or untrusted deployment output must never promote (task 4).
- Scheduled provider quota errors must not trigger redeployment or leak secrets (task 4).

### Task 1: Classroom and small product debt
**Files:** backend/practice/classroom.py, store.py, errors.py; site/practice.html, practice.mjs, learning.mjs; related tests (all under website).
**Interfaces:** Store.classroom retains exact response shape; normal reads use a bounded number of queries independent of student count. Error names remain import-compatible. Legacy replay correct events infer historical_unclassified until an explicit outcome supersedes them.
- [x] Add failing query-count tests at 1/30 students, old-bank/missing-progress and expired reservation projections; add legacy replay regression.
- [x] Run focused tests and confirm missing behavior fails.
- [x] Batch reads and ordered expiry processing; extract errors; remove redundant owner controls from practice; implement historical replay label.
- [x] Run backend/classroom/frontend suites and record before/after query counts, commit.

### Task 2: Development and quality tooling
**Files:** site/dev.mjs, package.json/lock, eslint.config.mjs; backend/requirements-dev.txt; Dockerfile; quality config and scripts/tests/test_configuration.py; website/README.md.
**Interfaces:** npm run build -> static; build:static alias; build:sites preserves Worker. npm run dev builds assets and spawns combined FastAPI server using PYTHON or python3 and --app-dir repository root; missing dependencies emit actionable error. Runtime requirement declarations must match.
- [x] Add failing command/runtime/config contract tests for static default, preserved Sites command and Python requirement consistency.
- [x] Resolve official current stable lint/test/audit/browser tool versions, pin them and install in development environment.
- [x] Implement launcher/config, basic Ruff F/E9 and ESLint correctness rules; remove actual lint findings without broad reformatting. Align Docker Python 3.12.
- [x] Run syntax/lint/config/unit/build/Sites compatibility and production dependency audits; investigate advisories rather than blanket exemptions; commit.

### Task 3: Migration and full-stack browser gates
**Files:** backend/tests/test_practice_migrations.py; tests/browser/conftest.py, test_workspace.py, support/server.py; pytest/config; production exclusion contract tests.
**Interfaces:** test-only ASGI fixture app uses synthetic bank references/retrieval/model and an isolated PostgreSQL schema. Chromium targets local real HTTP server. Migration test builds 001 with synthetic populated rows then upgrades to current.
- [x] Add failing migration-preservation and test-fixture packaging contract tests; run to verify missing behavior.
- [x] Add fixture server and browser flows for draft refresh, unit mistake/visual, helped correction, independent fresh follow-up, teacher evidence/replay, mobile widths and lock.
- [x] Run real Chromium and PostgreSQL migration tests; keep failure artifacts limited to synthetic data; commit.

### Task 4: Candidate release orchestration and monitoring
**Files:** scripts/release.py, scripts/deploy.py, scripts/tests/test_release.py and test_deploy.py; .github/workflows/ci-deploy.yml, monitor.yml; dependabot.yml.
**Interfaces:** release(run, transport, revision) builds/deploys --prod --skip-domain, checks candidate revision/readiness and disposable practice cycle, checks remote main then promotes and verifies public alias. Transport uses authenticated vercel curl for candidate, normal HTTP public alias. Live model probe is bounded/retry-aware and a separate monitor, never a release gate.
- [x] Write failing orchestration tests: candidate bad/stale/malformed output => no promote; healthy => promote once; alias failure => explicit recovery info, no DB rollback; transport sanitizes exceptions.
- [x] Implement injectable orchestration and deterministic practice smoke, provider Retry-After handling, split workflow triggers and production concurrency. Pin action references and use tested static artifact.
- [x] Add required quality/dependency/backend/migration/frontend/browser jobs with timeouts and narrow permissions; fork-safe fixtures; weekly grouped dependency PRs. Monitor has no deploy command/secrets beyond what its read requests need.
- [x] Run workflow validator, release tests, all quality gates and audits; commit.

### Task 5: Verification, report and review PR
**Files:** docs/verification/2026-11-14-ci-maintenance.md; plan/spec status; README guides.
**Interfaces:** report links exact checks and timings, query counts, dependency advisory results, retained debt and staged-release/database limitations.
- [x] Run full lint/tests/browser/migration/build/audit/workflow validation; document actual results and remaining gaps.
- [x] Request fresh whole-branch code review against approved spec and review focus; fix material findings with RED/GREEN regressions and full green suite.
- [x] Push separate stacked PR, attach it, wait for final-head CI; update report and deliver without merging/publishing.
