# Backbone guided-practice demo

Status: approved by Ronit, November 14, 2026; implement authorized.

## Purpose and decisions

Build a working company demo of course-grounded tutoring, extending Backbone's existing retrieval and Vercel website/API. Implement in the requested order: exercise bank, persistent sessions, workspace, checking, misconceptions, progressive hints. Ronit selected **Try as a student**, with saved progress and classroom replay, rather than full account registration.

Current public main is 05a7f48. The previous hosting work is pushed and merged; the original Georgia Tech checkout contains an older, uncommitted website snapshot and will be preserved. Work from the existing public checkout at /private/tmp/backbone-course-picker, on a new codex branch based on public main.

## Approaches

1. **Anonymous student demo with PostgreSQL and protected replay (selected).** Immediate entry, a persistent browser identity, meaningful classroom/session records, and a demo-owner replay view. Best fit for company reviewers trying the product.
2. Full student/teacher accounts. Supports real enrollment and cross-device login, but adds identity-provider setup and onboarding to the demo. Deferred.
3. Browser-only prototype. Easier to host but cannot satisfy PostgreSQL persistence, durable replay, or session isolation. Rejected.

Keep the existing FastAPI backend, plain JavaScript frontend, sanitized Markdown/math renderer, Groq model boundary, course-specific retrievers, Vercel deployment and private corpus handling. No new model vendor or credential is needed.

## 1. Structured exercise bank

Use **CS 2110**, whose private index contains 1,374 chunks from Patt & Patel (3rd edition) and lab slides. CS 2200 currently has original demo notes rather than an indexed textbook; do not claim otherwise.

Author 18 original exercises, six per topic, grounded in independently verified textbook and slide locations:

| Topic | Exercises |
| --- | --- |
| Number representation | Binary/hex conversion; decode signed two's complement; encode a negative integer; representable range; signed overflow; trace a bitwise operation |
| Memory and addressing | Address-space size; addressability versus address count; total memory capacity; byte/word units; LC-3 memory capacity; explain why equal address widths can describe different capacities |
| LC-3 execution | Trace ADD; trace AND/NOT; identify condition codes; calculate PC-relative target; trace a bounded straight-line snippet; explain LD versus LEA |

Each versioned record contains ID, topic, difficulty, prompt, input format and assumptions, expected answer, worked reasoning, rubric, accepted equivalences, common mistakes with evidence criteria, verified references, a three-step hint ladder, and a follow-up problem with its own answer/check metadata. Follow-ups remain linked extension problems rather than inflating the 18-exercise count.

References contain source title, textbook printed/PDF page or slide number, corpus chunk fingerprint and a verified supporting excerpt held privately. Bank definitions publish original questions and reference metadata only; never commit private source excerpts. A validation command checks every reference against the private corpus and produces a coverage report. Both textbook and slide evidence must support each selected topic; adjust individual exercises if that support cannot be established.

Expected answers, checker specifications and full hint ladders stay server-side. The student exercise API exposes prompts, input instructions and reference metadata only. Follow-up answers remain hidden until checked through the same pipeline.

## 2. PostgreSQL persistence and ordered events

Use psycopg with PostgreSQL, DATABASE_URL and versioned SQL migrations. No SQLite substitute. Local/CI PostgreSQL provides actual integration tests; the hosted database must be connected before claiming live persistence. Document a local container option. Provisioning a paid database is outside the selected design; use an existing or user-approved free service for deployment.

Tables: classrooms, students, classroom_memberships, exercise_versions, practice_sessions, exercise_progress, submissions, feedback, hints, session_events. Store structured bank definitions in versioned JSONB exercise rows. Sessions pin their bank version so subsequent edits cannot reinterpret old work. Submissions distinguish final answer from optional explanation/code and preserve the raw input.

Persist draft work (debounced), attempted checks, outcomes, hints, selected exercise and completion status. Successful assessment marks completion; uncertain assessments never do. Store model/checker versions and the sources actually used. The latest progress can be read directly; append-only events provide replay.

Allocate a strictly increasing per-session event sequence under a database row lock. Event timestamp is server-generated UTC; sequence defines order when timestamps tie. A submission/hint request is first durably recorded, then processed outside the transaction, then its result and associated progress/events commit atomically. Request idempotency keys prevent retries creating duplicate attempts or advancing hints twice. Concurrent draft writes use a revision check; an older browser cannot overwrite newer progress. Failed model calls preserve work and record a retryable failure without grading it incorrect.

## Identity and replay access

Try as a student creates a random student identity and membership in a seeded demo classroom, then a practice session. An opaque 256-bit token in a Secure, HttpOnly, SameSite cookie authorizes that student's records; store only its digest. Local HTTP development may relax Secure explicitly. Do not accept a client-supplied student ID as authorization. Validate same-origin writes and enforce request limits. Refresh restores identity and server state. Clearing cookies starts a new identity; cross-device recovery is outside this demo.

Show the student a replay of their own session. A classroom replay screen for the demo owner requires a separate server-configured owner token/session and never exposes all students to anonymous visitors. If no owner credential is configured, classroom-wide replay remains disabled; students still have personal replay. No identifying information is required beyond an optional display name. Explain persistence on entry and provide reset/delete-my-demo-data.

## 3. Student workspace

Add a Practice entry beside existing study chat, keeping chat usable.

Desktop sketch:

    Topics / progress | Exercise, assumptions, source references
    1. Numbers        | Final answer [                  ]
    2. Memory         | Show your work [explanation/code]
    3. LC-3           | [Check my work] [I'm stuck]
                      | Feedback / evidence / source-backed hints
                      | Attempt history [Replay] [Next exercise]

Use a stacked mobile layout. Label answer and explanation fields clearly; support plain text calculations and short LC-3 snippets, using existing safe rendering for feedback. Display saving/saved/retry state, accessible feedback status, progress counts and hint level. Persist before navigation and preserve drafts after refresh. Do not mark transient network errors as incorrect answers.

Replay steps through ordered timestamped events, showing the work, check result and hint visible at that moment. Do not synthesize fresh feedback during replay.

## 4. Topic-specific checking

Return one of correct, incorrect, needs_clarification, or unavailable. Feedback separates result correctness, reasoning support and system confidence. A correct final value with unsupported reasoning receives a targeted reasoning follow-up rather than blanket endorsement.

Deterministic checkers parse bounded arithmetic expressions, decimal/binary/hex literals, signed fixed-width values, explicit units and LC-3 register/condition-code results. Accept equivalent forms and calculations. Reject ambiguous units/formats with a clarification question. Never eval/exec student input or invoke a shell/compiler. A bounded LC-3 interpreter supports only the exercise's documented subset, fixed-width arithmetic, limited steps and no I/O; unsupported syntax/instructions yield clarification, not incorrect.

Written explanations use a defined exercise rubric plus the currently retrieved, verified supporting material through the existing Groq boundary. Request structured criterion-level judgments, exact supporting spans from student work, source IDs and uncertainty. Validate schema, quoted student spans and source membership on the server. Source IDs must refer to supplied evidence. Model failure, malformed output, contradictory evidence or unsupported judgment yields unavailable/needs_clarification. A rubric verdict is a fallible assessment, not a guarantee. Accept valid alternative explanations that meet the same conceptual criteria; do not require matching expected wording.

## 5. Misconceptions

For structured calculations/traces, compare interpretable intermediate steps in order and identify the earliest demonstrable error. For prose, return only a suspected misconception supported by an exact student quote and a source-backed rubric conflict. Distinguish first supported error from an assertion that it is necessarily the student's first actual error. Do not infer a misconception solely from a wrong final answer. If ordering or intent is unclear, quote the ambiguous step and ask one clarifying question. Store the evidence, criterion and clarification with the feedback.

## 6. Progressive grounded hints

Retrieve within CS 2110 using the exercise concept, verified reference anchors, prior attempts and hints. Prioritize the bank's verified source anchors; preserve stable source fingerprints and page/slide metadata in hint records. Validate citations against the actual retrieved chunks. If grounding is missing, report that help is unavailable rather than manufacture a reference.

Level 1 is a guiding question; level 2 names the relevant concept or relation; level 3 gives an exercise-specific intermediate step without the final answer. Use curated, reviewed ladder content linked to retrieved sources, with misconception-sensitive variants where evidence supports them. Do not place expected answers into the hint-generation context. A repeated request at the final level asks the student to try that step; it does not reveal the answer. Persist hint levels atomically with idempotency. The next check considers the work and hint history.

## Verification and delivery

Implement and verify the six stages in order. Add focused tests covering all 18 bank records and real corpus references; equivalent answers and units; LC-3 bounds; uncertain explanations; quote/citation validation; progressive hints; PostgreSQL migrations, ownership, transactional events and idempotency; refresh restoration; and replay fidelity. Extend GitHub CI with PostgreSQL integration tests and retain all existing chat/build checks. Use controlled model tests plus a small real-provider/source smoke check once configured; distinguish deterministic evidence from model quality.

Verify desktop/mobile workspace behavior, reload after a draft/submission/hint, isolation between two browser identities, and replay after a backend restart. Push the implementation branch and create a reviewable PR. Main merges automatically deploy production through existing CI, so do not merge merely to publish a preview. Hosted persistence additionally requires a valid PostgreSQL connection and migrations; report any unconfigured live dependency plainly.

## Builder-owned details and limits

Builder chooses table/index names, small-module boundaries, colors within the current visual system, migration tooling and exact original exercise values. Keep the system scoped to these topics. No unrestricted code execution, full LMS, grading integration, account administration, analytics dashboard or claims of measured learning improvement. Existing public chat behavior and private course-data boundaries remain regression requirements.
