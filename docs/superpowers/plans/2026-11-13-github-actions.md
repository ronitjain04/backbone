# GitHub Actions Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement these tasks.

**Goal:** Test and deploy Backbone automatically and daily.
**Architecture:** Parallel test jobs gate a main-only serialized deployment job. Render receives the tested commit through its deploy hook; health exposes the deployed commit. The frontend build becomes a Pages advanced-mode Worker artifact. Public smoke tests validate both courses and follow-up context.
**Tech Stack:** GitHub Actions, Python 3.11, Node 24, Wrangler.
**Spec:** ../specs/2026-11-13-github-actions-design.md

## Global Constraints
- Daily schedule 09:17 UTC; main deployments only after passing tests
- No credentials or private course corpus in Git, artifacts or logs
- Existing Cloudflare project backbone-study and existing Render service

## Review Focus
- Old backend must not satisfy deployment verification: match exact commit
- Missing credentials must fail before either deployment starts
- Fork PRs must never receive deployment credentials
- Cold starts and build delays need bounded retries
- Live inference must be exercised without logging private source excerpts

### Task 1: Release verification and smoke checks
- [ ] Add failing tests for health commit metadata, exact revision polling, bounded failures and smoke response validation
- [ ] Implement health revision and Python deployment helpers
- [ ] Run backend and deployment tests

### Task 2: Workflow and setup documentation
- [ ] Add test jobs, build artifact, guarded deployment, daily schedule and manual trigger
- [ ] Document credentials and recovery; validate YAML and run all tests/build
- [ ] Commit and push a PR, verify GitHub CI, configure credentials, merge and verify a production run
