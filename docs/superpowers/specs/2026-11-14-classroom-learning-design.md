# Interactive learning and classroom demo

Date: 2026-11-14. Status: proposed for approval.

## Intent and scope

Extend the deployed Backbone practice demo so company reviewers can see a student move from a supported mistake through help and correction to a fresh transfer check, while a teacher observes the evidence and replays the session. Build on the existing FastAPI, plain JavaScript, PostgreSQL/Neon, Groq rubric assessment, private course retrieval, 18 exercises, authored follow-ups, and ordered events.

Deliver the five requested parts together: one interactive explanation, assistance-aware follow-ups, live teacher dashboard, replay playback, and an evaluation report. Retain anonymous saved student sessions, one demo classroom, and protected teacher access using the existing owner credential. This is a demonstration of tutoring behavior, not a claim of measured learning efficacy. Do not introduce student accounts, a new model provider, paid infrastructure, arbitrary code execution, or unsupported diagnoses.

## Approaches and decisions

The implementation choice proposed by the builder is to extend the existing API and poll the teacher view every five seconds, using compact snapshots and loading detailed evidence only when requested. Student presence uses lightweight heartbeats. This reuses current hosting and authentication and is adequate for a 30-student demonstration.

SSE/WebSockets would update faster but add connection lifecycle and serverless hosting complexity. A separate realtime platform would add infrastructure and another security boundary. Neither is necessary for this demo. Existing styling, deployment, retrieval, and answer-checking boundaries remain the foundation.

## Student experience and interactive explanation

Keep the exercise, answer, attempted work, and feedback together. After a correct parent exercise, offer its existing authored follow-up with a different problem and the same concept. Enforce parent completion on the server for follow-up selection and submission. Do not reveal expected answers in public snapshots.

Add a memory explanation to the memory-capacity/addressability exercises (mem-03 and mem-06 and their follow-ups). Use explicit reviewed visual metadata in the bank rather than guessing parameters from prompt text. Display a small contrasting example: address bits determine the number of locations; addressability determines bits in each location. Let the student change address bits and bits per location, step through the two quantities, and compare total bits with bytes. Use a bounded grid with ellipses for large address spaces, exact numeric labels, keyboard-operable controls, and text equivalent.

Initially show a guiding question and a contrasting example, without substituting the active exercise values or exposing its expected answer. Increasingly specific stages explain the relationship and unit conversion. Each stage cites the existing verified source anchors and can open the source evidence. When there is a supported capacity/addressability diagnosis, show the exact submitted quote and highlight the relevant quantity. A numeric wrong answer alone is insufficient to identify that misconception: show a general explanation and a clarifying question instead. Never fabricate evidence or treat a hypothesis as confirmed.

Persist opening and stage changes before displaying assistance. Record visual parameters and stage in events; restore on refresh. These events also feed replay and assistance attribution. If saving fails, explain that the help cannot yet be opened and allow retry with the same idempotency key.

## Learning outcomes and assistance rules

Store completion separately from an assistance-aware outcome, with server-owned timestamps and provenance. Preserve first successful completion attribution so another submission cannot erase help already received. A parent or follow-up is `solved_independently` when correct without earlier conceptual assistance for that exercise. Assistance includes a delivered hint, opening the visual, or tutor feedback containing a supported conceptual diagnosis or corrective explanation. An incorrect response that only asks for an intermediate step, a parse clarification, and saving/replay do not themselves count as conceptual assistance. Self-correction without conceptual assistance can therefore remain independent.

A correct response after conceptual assistance is `corrected_with_help`. Not-yet-correct work remains in progress, with assistance history visible. Follow-up independence is assessed separately from the parent: help on the parent does not disqualify independent success on a fresh follow-up. Help on the follow-up does. Show parent outcome and transfer-check outcome side by side; do not imply that corrected work proves independent understanding.

The existing single authored follow-up per parent satisfies the fresh exercise requirement. Reopening it does not create a fresh problem or reset help. Completion history predating this release remains completed but its outcome is `historical_unclassified`, unless reliable provenance is explicitly migrated; default to that conservative label. Outcomes use stored facts, not client flags or a model's self-reported confidence.

## Persistence, concurrency, and authorization

Add an additive numbered SQL migration for outcomes, assistance provenance, persisted visual state, and per-tab presence. Introduce a migration ledger under the existing advisory lock, apply 001 compatibly to old databases, then apply later migrations in order. Preserve all existing rows and immutable bank versions. New reviewed visual metadata requires a new bank version; existing sessions retain their bank version and remain usable. The builder may define a safe version-resolution layer for shared presentation metadata without mutating old exercise definitions.

Use existing session ownership, session row locks, request-key idempotency, body validation, same-origin checks, and action limits. New mutations follow the same contract: same request key/body returns the original result, different body conflicts, concurrent duplicates create one event/outcome. Teacher endpoints require the owner credential and never expose token digests or raw connection credentials. Keep teacher credential in memory, not URL/localStorage. No public classroom listing or cross-student event access.

Track browser tabs independently with opaque tab identifiers and monotonically increasing presence messages so a delayed leave cannot override a newer heartbeat. Heartbeat approximately every 15 seconds while visible, reconnect immediately on visibility/network restoration, and send best-effort leave on pagehide. Presence uses server timestamps. Any recent active tab makes the session active. Last signal under 45 seconds is active; 45–120 seconds is stale; over 120 seconds or all known tabs explicitly left means disconnected/closed. Display these as observed signal states, not proof of network failure. Hidden/background tabs can become stale and that limitation is documented. Heartbeats do not consume tutoring quotas and do not append an event on every poll; record bounded connection/reconnection transitions only.

## Teacher dashboard

Add a protected teacher page and link from practice. After entering the existing teacher credential, show a compact live table and summary groups. Poll every five seconds while visible; stop overlapping requests, retain last good data on errors, display last refresh and connection error, and refresh immediately when visible again. No reload should be needed for new student activity. The builder may use a revision/cursor to avoid unchanged payloads.

Each row shows student display name and stable short session identifier, current exercise, recent meaningful activity, presence state, hints used, suspected misconception, parent outcome, and follow-up result. Distinguish activity from heartbeat time. Group students by authored concept and evidence-backed misconception category; show uncertain cases separately as clarification needed. Do not merge unrelated diagnoses based only on similar prose.

Selecting a student opens diagnosis evidence: exact quoted work, exercise/attempt timestamp, suspected misconception, clarification if applicable, and cited supporting material. Include a jump to that moment in replay. No diagnosis is shown without the evidence checks already enforced in assessment. Use readable empty, stale, unauthorized, and server error states. Avoid retrieving private course text for every classroom poll; fetch source detail only for authorized inspection.

Layout sketch:

    Classroom     Updated 2 seconds ago     [Refresh]
    Needs help: addressability (3) | Clarification needed (2)
    Student / Current exercise / Activity / Hints / Outcome / Signal
    Alex    / Capacity         / Checked  / 2     / Helped  / Active
    [Evidence: submitted quote, suspected mistake, sources, replay]

## Replay

Use a deterministic event reducer shared with frontend tests. Reconstruct saved work, submissions, recorded feedback, delivered hints, visual steps, completion outcomes, and follow-up state from persisted events. Never rerun retrieval or a model during replay. Preserve compatibility with older event types and show unknown historical classifications honestly.

Provide play/pause, timeline seeking, previous/next significant moment, and playback speed. Cap long inactive gaps so a demo remains usable; show real event timestamps and disclose skipped idle time. Pause on manual seeking and at the end. Highlight mistake evidence, hint, correction, and independent follow-up with accessible labels, not color alone. Plain numeric mistakes without supported diagnostic evidence remain labeled as incorrect attempts. Support the student's own replay and protected teacher replay through the same renderer. Source disclosures remain collapsed until requested.

## Accuracy and reliability evaluation

Create an executable, versioned fixture matrix covering correct answers, common mistakes, valid alternatives, ambiguous input, unsupported diagnoses, and answer leakage across existing topics. Test that exact evidence and verifiable source anchors are required, alternative correct calculations and supported LC-3 equivalents remain accepted, uncertainty remains distinct from incorrect work, and early hints/visual stages do not expose the current expected answer. Test assistance attribution, follow-up gating, historical compatibility, replay reduction, presence ordering/multiple tabs, authorization, idempotency, and migration preservation.

Run an isolated PostgreSQL classroom simulation with 30 students, teacher polling, persistence after reconnect, concurrent duplicate requests, and distinct assisted/independent flows. Keep production tutoring limits enabled: choose a workload fitting the 60 actions/minute budget (20 independent correct submissions and 10 sequences of wrong attempt, hint, correction, fresh follow-up = 60 actions); duplicates and presence requests are additional and must not consume tutoring quota. Exercise explicit throttling separately. Use a controlled model boundary for reproducible load and clearly label it; never load-test the production database or silently disable production limits.

Measure response latency by endpoint and report sample count, p50, p95, maximum, and errors with environment details. Separately run a small real hosted/model sample within provider limits if available. If credentials or hosting prevent that sample, document the gap rather than claiming measured model latency. Verify citation membership/fingerprint correctness separately from semantic source relevance; manually audit a stated sample for relevance and answer leakage. Do not conflate a valid anchor with proof of entailment.

Publish the exact commands, fixture counts and results, 30-student behavior, reconnect/duplicate outcomes, citation audit, measured latency, and limitations in docs/verification. Limitations include small authored bank, probabilistic explanation assessment, one follow-up per concept instance, polling delay, inferred presence, controlled load model, and no demonstrated educational efficacy.

## Delivery and acceptance

Implement and test locally against isolated PostgreSQL; verify additive migration on an isolated Neon development branch before a hosted review deployment touches it. Keep public production on the merged baseline until a new release is authorized. Build a reviewable branch/PR, run CI, verify desktop/mobile student and teacher flows and replay in browser, and report actual passing checks and remaining limitations. Do not expose course corpus excerpts, secrets, or student data in the public evaluation report.

The builder owns implementation details such as SQL indexes, exact component decomposition, visual bounds, playback interval, fixture organization, and compact dashboard payload format. Significant scope changes return to the user. Approval of this document authorizes implementation, testing, and a review PR; it does not itself request merging the new PR.
