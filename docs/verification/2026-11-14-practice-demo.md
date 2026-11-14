# Guided-practice implementation ledger

Plan: docs/superpowers/plans/2026-11-14-guided-practice.md
Spec approved by Ronit: November 14, 2026. Anonymous student entry selected.

- Previous work: public main 05a7f48 already contains the Vercel migration and hosting cleanup; no outstanding old changes needed pushing. The older Georgia Tech checkout was preserved.
- Task 1: complete — 18 original exercises, 18 follow-ups, 37 private-source anchors, fingerprint validation. Selected CS2110 rather than the CS2200 demo-note collection.
- Task 2: complete — actual PostgreSQL integration tests; versioned exercises, anonymous students/classroom membership, draft revisions, transactional ordered events, submissions/feedback/hints, deletion and non-identifying aggregate request budgets.
- Task 3: complete — separate practice workspace, cookie identity, refresh recovery, selected exercise, unsent draft recovery, personal and protected classroom replay.
- Task 4: complete — bounded arithmetic/units and fixed-width patterns, universal symbolic checking of the documented LC3 subset, source/rubric assessments with explicit uncertainty.
- Task 5: complete — first demonstrably false arithmetic step, fixed-width wrap handling, validated exact student evidence and source citations for suspected misconceptions. Wrong results alone do not imply a misconception.
- Task 6: implementation complete; hosted/visual verification in progress — reviewed three-level ladders retrieve verified course sources, preserve prior attempts/hints, and stop before disclosing the final answer. Lost-response retries keep idempotency IDs; interrupted requests recover after 90 seconds.

## Rulings and review

- Reuse the existing isolated public checkout; no additional worktree or copy of the old snapshot. Execute inline with an independent whole-change review.
- Use a bounded Z3 bit-vector proof rather than sample register states: alternatives must hold for every initial state, not just selected examples.
- Model assessments remain fallible. Validate exact evidence and source membership, but do not claim that validation proves the model's semantic interpretation.
- Original broad keyword source selection was narrowed to the actual supporting textbook paragraphs. Follow-up hints use follow-up values.
- Independent review identified fraction growth, wraparound grading, missing request quotas, missing required explanations, lost-response hint progression, and selected-exercise persistence. Each received a regression test and a fix.
- Re-review identified deletion-based quota bypass and hexadecimal-expression parsing. Independent budget buckets now survive student deletion; full expressions are parsed before trailing-unit interpretation.
- Shared global budgets span serverless instances; database integration tests use isolated temporary schemas so they neither alter the local demo nor accumulate rate-limit state.
- Ronit approved a free hosted database, then explicitly approved external PostgreSQL access and storing the connection in Vercel Secret settings. TLS is required. No plaintext credential was logged or committed.
- Created Render Free PostgreSQL `backbone-practice-demo` in the previously confirmed workspace, Virginia, PostgreSQL 17, 1GB. Expiration: December 14, 2026. No paid plan or automatic upgrade.
- Owner replay credential is stored in Vercel Secret settings and an ignored, mode-600 local file under website/.vercel/. Never put it in the PR or browser bundle.

## Demo walkthrough

1. Enter `/practice.html` and choose Try as a student.
2. On Read the bits, submit `46` without reasoning: the result is incorrect, but no misconception is invented; an intermediate step is requested.
3. Add work `32 + 8 = 40` then `40 + 4 = 46`: the first provable arithmetic error is quoted.
4. Request hints to see question → concept → intermediate step with source excerpts and stable citations.
5. Submit `32+8+4+1` as the final answer. Refresh to confirm progress and selected-exercise restoration.
6. On Write a bounded snippet, try `AND R0,R0,#0` / `ADD R0,R0,#4` / `NOT R0,R0`: a different valid solution is accepted for all initial registers.
7. Try Same width, different storage for a source/rubric explanation assessment. Treat the verdict as AI feedback, not an authoritative grade.
8. Open Replay my session and scrub timestamped events. Owner-only classroom replay is available through its separate access token.
