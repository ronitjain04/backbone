# CI/CD and maintenance verification — November 14, 2026

## Scope and audit findings addressed

This branch is stacked on classroom PR 12. It changes the active Vercel/FastAPI demo and its developer/release tooling, while preserving the still-active Sites publication and original historical applications. It does not merge a PR or publish a production release.

- Replaced promotion-before-verification with a production-configured candidate, authenticated candidate checks, a second main-revision guard, explicit promotion, and final public-alias revision verification. Failed/stale/malformed candidates cannot call promotion in deterministic orchestration tests.
- Separated daily live model monitoring from deployment. Main pushes are the only automatic release trigger. PRs no longer also run a duplicate feature-branch push workflow; superseded PR checks cancel, while workflows that may promote main are not canceled by later pushes.
- Added required basic lint, workflow validation, active-production dependency audits, populated-schema upgrade coverage and full-stack Chromium tests. The browser job downloads the exact static artifact from the frontend job; release reuses that same artifact. Fork PR jobs use only synthetic model/retrieval/teacher data and disposable PostgreSQL schemas.
- Pinned development tools, aligned Docker with the declared Python 3.12 deployment, and added a runtime dependency-declaration contract test to prevent pyproject/requirements drift. Updated artifact actions to immutable references for current official releases.
- Replaced the chat-only local preview with the combined FastAPI gateway, preserving an explicit Sites Worker build and its compatibility tests. Updated setup and hosting guidance. Removed 14 unused Python imports and one redundant JavaScript assignment, without broad legacy reformatting.
- Removed redundant owner/classroom controls from the student page; the protected teacher page owns those functions. Extracted shared persistence errors to remove circular Store/ClassroomStore imports. Historical replay correct-attempt events now show conservative historical completion until explicit newer outcome events supersede it.
- Batched classroom projections and sorted expired-session recovery locks instead of issuing multiple network queries for each student.

## Measured classroom change

A query-count regression first measured **6 SQL execute calls for one student and 151 for 30**. After refactoring, the normal no-expiry projection uses **2 for either size**. Expired actions require additional bounded recovery writes/locks; that exceptional path is not claimed to use only two queries. Tests cover concurrent teacher reads settling multiple expired sessions exactly once and preserving old bank-version behavior.

A repeated local ASGI + real PostgreSQL simulation retained all 30 students, 60 unique tutoring actions, 120 duplicate deliveries, 30 reconnects and ordered-event invariants. It used controlled fixture retrieval and no model calls. All 388 responses were HTTP 200; run time was 1.50 seconds.

| Classroom endpoint | Samples | p50 ms | p95 ms | Maximum ms |
|---|---:|---:|---:|---:|
| Earlier classroom implementation | 9 | 151.08 | 296.10 | 296.10 |
| Batched projection | 18 | 23.99 | 32.71 | 32.71 |

These separate local runs are a useful regression signal, not a controlled production benchmark or a model-throughput claim. Machine-readable [batched result](classroom-results/maintenance-batched.json); earlier result is preserved in [the classroom evaluation](2026-11-14-classroom-learning.md).

## Checks and tool versions

Local checks before independent review: **170 Python backend/deployment tests, 50 JavaScript tests, 2 real Chromium full-stack flows**, Ruff, ESLint, checksum-verified actionlint, static build, and retained Sites Worker compatibility build passed. After the independent review fix pass and retryable-503 extension: **177 Python tests, 50 JavaScript tests and 2 Chromium flows passed**, with lint/workflow/build checks green. Final GitHub CI is verified on the pushed PR head before handoff.

Pinned tools verified against official PyPI/npm registries: pytest 9.2.0, Ruff 0.17.5, pip-audit 2.10.1, pytest-playwright 0.10.0, Playwright 1.65.2, ESLint 10.15.0, @eslint/js 10.0.1 and globals 17.14.0. Node 24 and Python 3.12 are CI targets; local Python tests also ran on the existing 3.11 development environment. Actionlint 1.7.12 archives are checked against their official SHA-256 checksums; artifact actions are pinned to official upload-artifact 7.0.2 and download-artifact 8.0.2 commits.

Production dependency audit: **27 resolved Python packages, zero known vulnerabilities**; npm production audit, **zero known vulnerabilities**. No advisory was suppressed or blanket exception added. These scans cover current production dependencies, not every historical project or future vulnerability. Dependabot opens weekly grouped update PRs and does not auto-merge them.

The populated migration test constructs schema 001 with a synthetic student, membership, immutable exercise, completed work, hint count, draft revision and recorded feedback event, then applies/reruns current migrations. Data remains intact and historical completion is not relabeled independent.

Chromium verifies the actual local HTTP gateway and PostgreSQL persistence: submitted unit mistake, source-grounded hint/visual, saved visual stage and draft after refresh, helped correction, independent fresh follow-up, teacher authentication/outcomes/evidence/replay/lock, and 390px student/teacher page bounds. Browser fixtures are outside the Vercel project root and never use a private corpus or real model credential. Failed traces/screenshots contain only synthetic data and have three-day retention in CI.

## Release/monitor safety evidence and limits

Tests prove candidate failure, stale main and invalid URLs prevent promotion; promotion occurs once only after verification; a failed final alias check reports the previous code deployment and does not attempt a destructive database rollback; raw command errors are sanitized. The candidate smoke checks actual HTML/JavaScript assets, exact revision and both course configurations, then creates a fresh disposable student to verify saved work, grounded deterministic checking, duplicates, completion, contiguous replay and the teacher boundary. It deletes only that new session, including on a failed check. A real local fixture-API integration test exercises the smoke, not only response mocks.

Release orchestration was **not executed against production** because this scope is a review PR, not authorization to publish. Vercel CLI candidate/promotion help and the pinned CLI's machine deployment output shape were checked; the live promotion/alias path still needs its first authorized main release. Provider checks are separated from deterministic release gates: the read-only scheduled/manual monitor uses bounded retries and respects Retry-After, reporting a long quota window without retrying early. Provider/service/network availability failures remain distinct from an invalid response/source contract; no private source excerpts are printed.

An unpromoted production-configured candidate still shares production database settings and application startup may apply additive migrations. Candidate staging protects code/domain promotion, **not schema isolation**. Migrations must remain compatible with the previous app. A code rollback command cannot undo database changes. Rollback identification uses authenticated Vercel control-plane metadata rather than application health, so a broken app does not prevent shipping its replacement. The previous workflow-level concurrency name is preserved to serialize against an older release already in progress. Provider/local rate limits retain a sanitized numeric Retry-After through the actual public gateway; regressions prove the monitor does not retry before a 3600-second provider delay for either HTTP 429 or HTTP 503. Classroom polls skip sessions deleted between expired-action discovery and locking.

Main-revision checks reduce stale promotion risk but cannot make a Git push and Vercel promotion one atomic cross-service operation.

## Independent review

The reviewer found no Critical issues and four Important issues: concurrency across old/new workflow revisions; delete-versus-expiry recovery; lost public retry timing; and recovery metadata depending on app health. Five regression cases reproduced these gaps before fixes, and the full suite then passed. No Minor findings were deferred. The reviewer did not execute a production release, inspect production credentials/database state, certify legacy security, or independently rerun the supplied browser/audit checks. Those remain explicit scope/evidence limits, not inferred guarantees.

## GitHub delivery evidence

[PR 13](https://github.com/ronitjain04/backbone/pull/13) is stacked on classroom PR 12, which remains unchanged. [Source verification run 43660517335](https://github.com/ronitjain04/backbone/actions/runs/43660517335) passed quality/workflow/dependency, frontend/static build, backend/migration/release tests and full-stack Chromium jobs on Python 3.12/PostgreSQL 17. Browser CI successfully downloaded the upload-artifact v7 artifact through download-artifact v8. Production promotion was skipped for this PR as intended. The final PR-head checks are reverified before handoff.

The first CI run found a clean-checkout fixture dependency: the backend release-smoke integration expected locally generated frontend assets. Its fixture now provides synthetic static files explicitly, and all 176 backend tests passed with generated `website/public` temporarily absent. Chromium continues checking the actual uploaded release artifact. This fixed test isolation without bypassing production asset verification.

## Retained debt / deliberate boundaries

- The Sites connector confirmed the older publication is active at version 6. Its Worker gateway, explicit `build:sites` command, source identity and compatibility tests remain. This is a real consumer, not dead code to delete blindly.
- Original `backbone-ui` and `backbone-i2p` projects retain their source/attribution. Their older rendering and dependencies were inventoried but not security-certified or rewritten by this change.
- Direct PostgreSQL connections, model quota/semantic limitations, the authored exercise bank size, and application startup auto-migration remain documented limitations rather than hidden infrastructure changes.
- This change adds correctness lint, not wholesale formatting or an invented coverage-percentage target. Pinned direct development tools improve reproducibility; transitive package installation and advisory databases can still change and are checked by CI.

## Reproduction

```sh
python -m pip install -r website/backend/requirements.txt -r website/backend/requirements-dev.txt
npm --prefix website/site ci
ruff check .
npm --prefix website/site run lint
# TEST_DATABASE_URL must identify a disposable local/CI database.
python -m pytest website/backend/tests scripts/tests -q
npm --prefix website/site test
npm --prefix website/site run build
npm --prefix website/site run build:sites
python -m playwright install --only-shell chromium
python -m pytest tests/browser --browser chromium --tracing retain-on-failure --screenshot only-on-failure -q
pip-audit -r website/backend/requirements.txt
npm --prefix website/site audit --omit=dev --audit-level=high
# actionlint binary must match the official 1.7.12 checksum before execution.
actionlint
```

Do not run `python -m scripts.release` locally as a verification shortcut: it is a publishing operation intended for the gated, authorized main-release job.
