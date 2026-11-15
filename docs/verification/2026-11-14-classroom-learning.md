# Classroom learning verification — November 14, 2026

## Delivered behavior

- Memory diagram on mem-03/mem-06 and their follow-ups: reviewed contrasting example, three stages, adjustable address width/addressability, exact supported mistake quote when available, and verified source disclosures. Opening it is persisted as help before display.
- Server-owned first completion outcomes distinguish corrected with help from independent success. Follow-ups have different authored values, are gated by parent completion, and have their own assistance history. Unresolved hint reservations temporarily defer independence; expired workers are finalized on refresh, new actions, or teacher reads.
- Protected `/teacher.html` polls every five seconds, shows current exercise, meaningful activity, hints actually delivered, parent/follow-up outcomes, diagnosis evidence, authored concept groups and inferred connection signals. Evidence and replay are loaded only on inspection. Teacher token stays in page memory.
- Student and teacher replay reconstruct stored attempts, feedback, visual settings, help and outcomes. Play/pause, speed, timeline, significant-moment navigation and quoted evidence use recorded events, without rerunning the tutor. Long idle gaps are compressed and labeled.

Review deployment: https://backbone-m62uzldp3-ronit-jain.vercel.app/practice.html (application commit `133e9fe`). Teacher page is at the same origin, `/teacher.html`. Vercel deployment access and the application teacher credential remain separate. Public production was not promoted by this work.

PR: https://github.com/ronitjain04/backbone/pull/12. GitHub Actions backend/deployment tests and frontend tests/build passed on both push and PR runs. Production deployment is intentionally skipped for this feature branch.

## Automated checks

Local complete suite: **142 Python backend/deployment tests passed; 48 JavaScript frontend tests passed; static build passed**. Python 3.11, Node 24, real PostgreSQL in an isolated schema. CI uses Python 3.12 and PostgreSQL 17.

The explicit evaluation matrix contains 15 deterministic cases spanning correct answers, common mistakes, valid alternative calculations/code, ambiguous input, and adversarial syntax; five rubric cases for supported evidence, missing evidence and invalid citations; and a leakage/source-membership check over all 36 parent/follow-up first hints plus all six memory visual stages. Existing tests additionally check all authored deterministic expected answers/follow-ups, bounded LC-3 equivalence, first supported arithmetic errors and signed wraparound. Added unit equality cases distinguish explicit bits/bytes/KiB from missing or ambiguous units.

Regression tests cover parent/follow-up attribution, immutable first outcomes, historical completion, overlapping hint/check requests, abandoned-worker recovery, late worker rejection, follow-up gating, duplicate visual recovery when retrieval disappears, explanation evidence in Final answer, ordered multi-tab signals, teacher authorization, markup treated as literal text, failed polling retaining last good data, and eight concurrent reservations/completions for a single request key. Separate quota tests reject a 61st action while cached retries remain free.

## Thirty-student reliability and latency

[Machine-readable local result](classroom-results/local-30-students.json). This is **local ASGI + real PostgreSQL with a controlled retriever and no model calls**, not a production/provider capacity claim.

Thirty simulated students ran concurrently with ten workers. Twenty solved an original exercise independently; ten submitted a supported unit mistake, requested a hint, corrected the parent, and independently solved its fresh follow-up. Teacher reads ran concurrently. Results:

- 60 unique tutoring actions; 120 duplicate HTTP deliveries returned the cached result without additional tutoring budget.
- 30 reconnects restored completed state; delayed old leave signals could not override newer heartbeats.
- Exactly 50 check-request events, 10 hint-request events, and 40 outcome events; every session had contiguous event sequence numbers.
- Ten helped corrections and 30 independent solutions (20 originals plus 10 follow-ups).
- 379 HTTP responses, all 200; total run 2.08 seconds. Production action limits remained enabled.

| Endpoint | Samples (includes cached retries) | p50 ms | p95 ms | Maximum ms |
|---|---:|---:|---:|---:|
| Check | 150 | 61.66 | 127.25 | 173.00 |
| Hint | 30 | 61.74 | 124.69 | 128.82 |
| Classroom | 9 | 151.08 | 296.10 | 296.10 |
| Presence | 90 | 30.91 | 39.43 | 58.77 |
| Reconnected state | 30 | 37.70 | 56.35 | 58.45 |

Percentiles use nearest-rank order statistics. Local numbers exclude internet latency, cold starts and model inference. These small samples are reproducible checks, not performance guarantees.

## Hosted model and citation sample

The hosted review used the existing Groq `openai/gpt-oss-20b`, the actual private course corpus and the isolated Neon review branch. Six cases exercised alternative explanations/calculations, an addressability misconception, ambiguous input, LD versus LEA, and a deterministic first-error check. Disposable evaluator sessions were deleted after their individual runs.

**Initial burst: 3/6 expected statuses matched.** Two explanation requests became unavailable and one correct calculation with reasoning fell back to clarification. Runtime logs contained three provider HTTP 429 responses in this sample window. The app did not incorrectly mark unavailable assessments as incorrect work. This is an observed provider quota limitation and is retained in the [burst artifact](classroom-results/hosted-burst.json).

**Paced sample (35 seconds between cases): 6/6 expected statuses matched.** Median HTTP time was **1,396.22 ms**; p95/maximum **1,892.24 ms**, n=6. Four responses identified the model, one ambiguous response used a conservative clarification fallback without model provenance, and one was a deterministic equality diagnosis. These statuses do not establish a general model accuracy rate. [Paced artifact](classroom-results/hosted-paced.json).

All **16/16 returned source excerpts** in the paced sample matched corpus source/details/SHA-256 exactly; all supported misconception quotes were verbatim submitted text. Separately, the bank validator found **37/37 authored source anchors valid**. Manual inspection of four exercise anchor sets (mem-03, mem-06, lc3-06, num-01) confirmed relevant support for capacity/addressability, LD versus LEA, and binary representation. Citation identity is machine-verified; full semantic entailment is not automatically proven. No private source excerpts are included in these published artifacts.

## Hosted migration and browser checks

Created Neon review branch `classroom-learning-review` (`br-billowing-king-bbpy4yxb`) from production, then ran both migrations and a rerun against that isolated copy. Before/after student, event and progress row counts matched; nine existing completed records received historical-unclassified outcomes. Production Neon and the read-only Render rollback copy were unchanged.

Browser verified on hosted review: exact unit mistake evidence linked into the visual; stage restoration after refresh; corrected-with-help parent; different independently solved follow-up; replay play/pause and supported-mistake navigation; protected teacher login, outcome summaries, evidence inspection and replay jump; lock clearing the private view. Checked desktop at 1440×1000 and phone width 390. Mobile header overflow found and fixed; final student page width equaled viewport width (390), including the open diagram. Teacher table scrolls inside its container (800px table within 352px container), without widening the 390px page. Temporary viewport overrides were reset.

## Reproduction

```sh
# Set TEST_DATABASE_URL privately to an isolated local PostgreSQL database.
python -m pytest website/backend/tests scripts/tests -q
npm test --prefix website/site
npm run build:static --prefix website/site
python -m website.backend.tools.evaluate_classroom --output /tmp/classroom-results.json
python -m website.backend.tools.validate_practice_sources /private/path/cs2110/corpus.jsonl
# Requires an authorized Vercel login, linked website project and private corpus.
python -m website.backend.tools.evaluate_hosted_practice \
  --base-url https://YOUR-REVIEW.vercel.app \
  --corpus /private/path/cs2110/corpus.jsonl \
  --delay-seconds 35 --output /tmp/hosted-results.json
```

The local evaluator refuses remote hosts and creates/removes only its unique test schema. Never point load testing at a hosted production database. The hosted evaluator makes only its six cases, uses Vercel's authenticated curl for protected deployments, and measures curl HTTP time rather than CLI startup overhead.

## Limitations

- Free model quota can interrupt a rapid demonstration; 30 simultaneous model-backed assessments were **not** tested. The classroom load test exercises persistence and API reliability with controlled retrieval, not provider throughput.
- Explanation assessment remains probabilistic and may clarify instead of accepting valid reasoning. Evidence membership and citation fingerprints do not prove every diagnosis or claim correct. No learning efficacy study was conducted.
- There is one authored follow-up per parent, not an unlimited fresh-problem generator. Reopening never resets assistance history.
- Five-second polling adds delay; browser background throttling can produce stale signals. Disconnected/closed is inferred, not proof of network failure. The dashboard shows up to 100 newest demo sessions in one classroom.
- Historical sessions retain completion but do not gain invented independent classifications. Deferred minor: legacy replay correct-attempt events lack an explicit historical-unclassified badge; the dashboard and saved progress label these historical outcomes conservatively.
- Existing direct PostgreSQL connections remain; no pooler compatibility or large sustained production-load claim was added.
