# Follow-up conversations implementation plan

Goal: Support references such as “why?” and “show another example” within each
course, and deliver the change as a separate PR based on the open formatting PR.

The browser retains up to four completed exchanges per course in memory, with
at most 8 messages, 4,000 characters per message and 16,000 total history
characters. Only successful exchanges enter context. Clear chat resets that
course's messages, draft, errors and history; refresh also clears context.

History contains user/assistant roles only, alternating complete pairs. Both the
Worker proxy and FastAPI validate it. Request bodies are capped at 128 KiB.
For a follow-up, the existing model provider rewrites the latest question into a
standalone retrieval question, leaving self-contained topic changes intact.
Retrieval remains confined to the selected course. The answer receives recent
chat as context, but only current source excerpts count as evidence/citations.
Rewrite plus retrieval plus answering share a 60-second deadline. No server-side
conversation store or new credentials are introduced.

- [x] Add failing backend tests for contextual retrieval, course isolation,
      invalid/bounded history, low grounding, rewrite failures and provider payloads.
- [x] Implement history schemas, standalone-question rewriting and grounded
      answer context for compatible providers and native Ollama.
- [x] Add failing proxy/browser tests for validated forwarding, old upstream
      capability checks, per-course context, failed requests and Clear chat.
- [x] Implement shared browser/proxy context limits and update user-facing copy.
- [x] Run complete suites/build, check a local conversation flow in the browser,
      get an independent code review, and open a focused separate PR.

Validation: 34 backend tests and 36 frontend tests passed, including the production Worker build. The existing Starlette/httpx deprecation warning remains. Local browser QA used real course retrieval and a controlled HTTP model boundary: a global-bus question followed by “Why?” preserved context, switching courses isolated messages, and Clear chat reset the context. Browser console had no errors. Independent review found no actionable issues. Live model rewrite quality has not been exercised; this change is delivered for PR review without production deployment.
