# Backbone website

A responsive introduction and live study chat, with source excerpts. The Python API performs retrieval before asking an HTTP model provider to explain. No prepared answers replace model calls.

## Current state

The Vercel website and API are deployed and connected to Groq using GPT-OSS 20B. A complete live answer with source excerpts was verified through the published website. The website is public at [backbone-study.vercel.app](https://backbone-study.vercel.app). The configured readiness endpoint checks loaded resources and model settings, not provider availability or remaining quota; inference remains subject to provider limits.

Assistant answers render Markdown, syntax-highlighted C/C++ and LC-3 code, and inline/display TeX equations. The renderer disables raw HTML, sanitizes its output, and keeps questions and retrieved excerpts literal. Invalid equations remain readable. Browser dependencies, KaTeX styles, and WOFF2 math fonts are bundled and served from the same origin; code blocks, tables, and display equations scroll within the answer. KaTeX layout requires inline style attributes; inline scripts remain disallowed by CSP.

The website has CS 2110 and CS 2200 tabs with separate local chat histories and drafts. Every question carries a validated course ID, and each course has its own retriever. An unavailable course returns an explicit error instead of using another course’s material. Switching tabs during an answer keeps that response in its original course.

The CS 2200 starter collection contains six **original demo notes**, not Georgia Tech slides or textbook excerpts. Production private course data is not included. The default demo uses lightweight lexical retrieval; optional `RETRIEVAL_MODE=semantic` uses normalized sentence embeddings and a FAISS inner-product index. The previous sibling app's API contract and grounding approach are preserved; this deployment uses explicit JSONL documents rather than runtime pickle loading.

## Local preview

Node.js 24 is the tested website build/preview baseline. From the repository root:

```sh
npm --prefix website/site ci
node website/site/dev.mjs
```

Open http://127.0.0.1:4173. The introduction and chat are available immediately; without backend configuration, sending a question displays an honest service-not-connected message and preserves the question.

## Start a live backend

Python 3.11 is the tested baseline. Create an environment and install:

```sh
python3 -m venv website/.venv
website/.venv/bin/pip install -r website/backend/requirements.txt
```

Set the values from `backend/.env.example` in your shell or hosting secret manager. `.env` files are examples only and are **not automatically loaded**. Never place keys in browser files or command-line arguments. `MODEL_PROVIDER=compatible` uses a chat-completions-compatible HTTP API; `MODEL_BASE_URL` includes its version prefix. `MODEL_PROVIDER=ollama` uses the native `/api/generate` endpoint and the origin as its base URL. Set the provider's real model name and credential. No external inference key is created by this project.

```sh
export CORPUS_PATH=website/backend/data/demo.jsonl
export RETRIEVAL_MODE=lexical
website/.venv/bin/uvicorn website.backend.app:app --host 127.0.0.1 --port 8000
```

For the website preview, set `BACKEND_URL=http://127.0.0.1:8000` and the same `BACKEND_TOKEN` as the API, then restart `node website/site/dev.mjs`. `/health` checks process liveness; `/ready` returns 503 until the corpus and model settings load and a backend token is configured. Ten chat attempts per minute per backend process limit inference traffic. Use one worker for this process-wide budget; multi-instance deployments need a shared limit. No conversation history is stored server-side. The browser sends bounded recent context for the selected course with each request; refreshing or clearing that course’s chat resets its context.

## Host the backend

The Docker build context is the repository root:

```sh
docker build -f website/backend/Dockerfile -t backbone-api .
```

Connect a sanitized repository to Render and set the Blueprint Path to `website/render.yaml`, or use the Dockerfile on another compatible host. The Blueprint configures the original demo corpus and prompts for inference settings; it generates a backend token. Choose and review the hosting plan in your hosting account; no paid service has been provisioned by this project. See [Render's Blueprint reference](https://render.com/docs/blueprint-spec).

Keep `MODEL_API_KEY` and `BACKEND_TOKEN` in the host's secret manager. Configure `BACKEND_URL` and the matching `BACKEND_TOKEN` as Sites runtime environment values. Keep the backend behind TLS and the token gate. The API deliberately exposes no cross-origin browser access; browsers use the same-origin website proxy.

For semantic retrieval, install `backend/requirements-semantic.txt` in a suitable image and set `RETRIEVAL_MODE=semantic`. This requires more memory and a downloaded embedding model and has not been exercised by the lightweight test suite. For private corpora, mount UTF-8 JSONL files outside the source checkout and set `CS2110_CORPUS_PATH` and/or `CS2200_CORPUS_PATH`. The legacy `CORPUS_PATH` remains a CS 2200 fallback. Each course loads independently, so a missing CS 2110 file does not take CS 2200 offline. `/ready?course=cs2110` and `/ready?course=cs2200` report per-course configuration; `/ready` succeeds when at least one course is configured. Chat bodies accept `{ "query": "…", "course": "cs2110" }` (default course: `cs2200`). Each line must have nonempty `text` and `source` strings and an optional `details` string. Split excerpts into chunks under 10,000 characters. Do not publish lecture slides, textbooks, extracted course chunks, or indexes in the frontend or source repository.

## Follow-up conversations

Each course keeps up to four completed exchanges in browser memory. Follow-ups
such as “why?” or “show another example” include only that course's recent
user/assistant messages. Clear chat resets the selected course's context; the
other course is unaffected. Failed requests and pending answers are not added.
Nothing is persisted across refreshes or stored in a backend session database.

Chat requests accept an optional `history` array of `{role, content}` messages.
Only alternating, completed user/assistant pairs are allowed: at most 8 messages,
4,000 characters per message and 16,000 total context characters. The browser
truncates long messages with a marker and drops the oldest complete pairs to fit.
The Worker proxy and API validate history; the proxy and dev server cap encoded
request bodies at 128 KiB. Existing requests without history remain valid.

For a request with history, the model first rewrites the latest question into a
standalone retrieval question, resolving references while preserving topic
changes. Retrieval still searches only the selected course. The answering model
receives the original question, recent chat and freshly retrieved excerpts; it is
instructed to use only the current excerpts as evidence and to refresh citations.
A lack of relevant current sources produces the existing grounding refusal.
Native Ollama and compatible HTTP providers both support this flow. A follow-up
uses an additional model call for rewriting, so it can take longer and consume
more provider quota. Rewrite, retrieval and answering share a 60-second deadline.
Malformed/truncated rewrites and provider failures fail closed with a retryable
service error, preserving the student's draft and previous completed history.

Deploy the updated backend before the updated website: API chat responses expose
`supports_history: true`. The proxy refuses follow-ups if an older upstream does
not advertise that capability, instead of silently discarding context. Model
provider retention settings also apply to the recent messages sent for rewriting
and answering; keep provider credentials server-side.

## Import CS 2110 privately

The importer follows the supplied **Fall 2026 syllabus**, including its listed
introductory C++ readings. It excludes chapter 10, section 8.3, chapter exercises,
appendices and answer keys. The syllabus names stacks but cites 8.1 (subroutines),
so 8.2 is included for that named topic. Lab decks supplement the textbook.

Install the optional import dependencies separately from the lightweight API:

```sh
website/.venv/bin/pip install -r website/backend/requirements-ingest.txt
website/.venv/bin/python website/backend/tools/prepare_cs2110.py \
  --input "/path/to/your/course/folder" \
  --output website/private-data/cs2110
export CS2110_CORPUS_PATH="$PWD/website/private-data/cs2110/corpus.jsonl"
```

The input folder contains `Syllabus Fall_2026.pdf`, the third-edition textbook PDF
whose filename starts with `Introduction`, and lab `.pptx` files (nested folders
are supported). The importer writes a JSONL corpus, source-hash manifest, and a
compressed plaintext envelope, `cs2110.jsonl.gz.b64`. Textbook references include
both printed and PDF page numbers; labs include slide numbers. Identical slide
text is deduplicated while its alternate references remain in the manifest.
Superscripts are preserved when detected; diagrams, screenshots, handwriting and
speaker notes are not interpreted. The manifest lists blank and sparse slides.

The three supplied acceptance questions concern the LC-3 global bus, memory
addressability, and `typedef` with structures. Check retrieval against those
questions after importing. They are not replaced with canned model answers.

For a host supporting plaintext secret files, upload the generated
`cs2110.jsonl.gz.b64` through its private configuration, then set
`CS2110_CORPUS_PATH=/etc/secrets/cs2110.jsonl.gz.b64` and redeploy. The backend
recognizes that exact suffix and decompresses in memory with a 20 MiB expanded
limit. Keep the existing CS 2200 configuration and model credentials. Neither
private output format belongs in Git, the browser bundle or the public image.
The course picker alone does not install course data on the server.

## Publish the website

`site/.openai/hosting.json` stores the exact Sites identity. `node website/site/build.mjs` generates a self-contained Worker at `site/dist/server/index.js`. Package and publish using the Sites source workflow; browser libraries and math fonts are bundled locally; the deployed Worker has no Node.js runtime dependency. Publish only `website/site`, not this whole repository. New Sites are private by default; wider tester access must be configured with supported Sites controls.

## Verify

```sh
website/.venv/bin/pip install pytest
website/.venv/bin/python -m pytest website/backend/tests -q
node --test website/site/tests/*.test.mjs
node website/site/build.mjs
node --check website/site/dist/server/index.js
```

Before calling it a working live demo: check `/ready`, submit a real question through the published website, inspect its returned sources, and verify visitor access. Unit tests use a controlled model boundary and do not prove a hosted model is running. Inference requests send the question and retrieved excerpts to your configured model provider; configure its retention and privacy settings accordingly.

## Entire site on Vercel

The public site is [backbone-study.vercel.app](https://backbone-study.vercel.app). Its browser assets and API deploy together in the existing Vercel project. The website gateway calls the authenticated backend in the same process, keeping credentials out of browser code. The backend runs as a Python 3.12 FastAPI function on Vercel Hobby, with a 120-second function limit. Hosting and model quotas still apply. Startup and model-response latency vary; this removes Render's minute-long idle wake-up behavior rather than guaranteeing a fixed response time.

Deploy from `website/`: `.python-version`, `pyproject.toml` and `vercel.json` configure the runtime and entrypoint. Build browser assets with `npm --prefix website/site ci` and `npm --prefix website/site run build:static` before deployment. Only the asset whitelist is written to `website/public/`, which Vercel serves through its CDN. `.vercelignore` excludes frontend source files, local credentials, private corpora and development environments from source uploads. Private CS 2110 data is loaded in memory through the official Vercel Blob SDK; the complete corpus has no public download route and is never committed. Vercel Blob must be **Private**, with `CS2110_CORPUS_BLOB=courses/cs2110.jsonl.gz.b64`. `BLOB_STORE_ID` identifies the connected store. Use the store's encrypted `BLOB_READ_WRITE_TOKEN` or Vercel's project-bound OIDC identity. The loader bounds encoded and expanded data at 20 MiB. The CS 2200 collection remains `CORPUS_PATH=backend/data/demo.jsonl`.

Keep `MODEL_API_KEY` and `BACKEND_TOKEN` as production **Secret** values in Vercel. Configure `MODEL_PROVIDER`, `MODEL_BASE_URL`, `MODEL_NAME` and `RETRIEVAL_MODE` there as well. The public gateway uses the existing token internally; no Cloudflare configuration is required. Do not put these secrets in browser files. Secret environment values cannot be downloaded through `vercel env pull`; it returns placeholders for them.

## Automated tests and deployment

[GitHub Actions](https://github.com/ronitjain04/backbone/actions/workflows/ci-deploy.yml) runs the frontend suite/build and Python backend/deployment suite on pushes and pull requests. Successful `main` runs deploy production, as do manual runs on `main` and the daily **09:17 UTC** schedule. GitHub may delay scheduled runs. Pull requests and other branches never deploy.

Configure these repository Actions settings:

| Setting | Type | Purpose |
| --- | --- | --- |
| `VERCEL_ORG_ID` | Variable | Vercel account/team owning `backbone-api` |
| `VERCEL_PROJECT_ID` | Variable | Existing combined website/API project ID |
| `VERCEL_TOKEN` | Secret | Project-scoped deployment access |
| `BACKEND_URL` | Variable | `https://backbone-api.vercel.app` |

The workflow fails before deploying if any setting is absent. The pinned Vercel CLI uploads the checked-out API and tested frontend artifact together, waits for deployment completion, and assigns the production `backbone-study.vercel.app` alias. `BACKBONE_COMMIT` records the tested SHA in the function environment; `/health` must match that SHA and `/ready` must include both courses before the public website smoke tests run. Keep Vercel's independent Git auto-deployment disconnected so GitHub's test gate controls releases.

Public smoke checks request real answers for both courses plus a contextual follow-up, requiring sources and conversation support. This uses three answers and one query rewrite per deployment and does not print private source excerpts. The inference budget is per function process, not a global limit across Vercel instances; provider quotas still constrain use. Model/provider outages fail verification even if deployment succeeded. Rerun from **Actions → Test and deploy Backbone → Run workflow → main** after fixing an outage. There is no automatic rollback.

Production hosting and automated releases use Vercel only. The old Cloudflare Pages project is no longer required, and GitHub Actions does not need Cloudflare credentials. Use Vercel deployment rollback to restore an earlier combined release. The previous Render service is outside the active deployment workflow.

## Guided practice demo

Open `/practice.html` for 18 original CS 2110 exercises: number representation,
memory/addressing, and LC-3 execution. Each has an answer, worked reasoning, rubric,
common mistakes, verified textbook/slide references, a three-level hint ladder and
an independently checkable follow-up. Answers and check specifications are served
only by the backend. Private textbook excerpts remain outside Git and browser assets.

Practice needs **PostgreSQL**, independently of the existing chat. Install the
updated backend requirements, set `DATABASE_URL` securely, then run:

```sh
python -m website.backend.tools.migrate_practice
python -m website.backend.tools.validate_practice_sources /private/path/to/cs2110/corpus.jsonl
npm --prefix website/site ci
npm --prefix website/site run build:static
python -m uvicorn website.backend.site:app --host 127.0.0.1 --port 8000
```

Use the combined Python server for practice, not the legacy Node chat-only preview.
Set `CS2110_CORPUS_PATH` locally (or retain the Vercel private Blob configuration)
and the existing Groq model settings for written reasoning assessments. The bank
is pinned to source fingerprints: if a corpus changes, reverify/update its anchors
and increment `BANK_VERSION` and every exercise version. Existing sessions keep
using their pinned definitions. `PRACTICE_AUTO_MIGRATE=1` may bootstrap the new demo
database at application startup; leave it unset when applying migrations separately.

For a disposable local database, with Docker running:

```sh
docker run --name backbone-practice-pg -e POSTGRES_PASSWORD=local-demo-only \
  -e POSTGRES_DB=backbone -p 127.0.0.1:5432:5432 -d postgres:17
```

Configure the corresponding local URL through your shell/environment manager;
never commit a real connection credential. Hosted connections must use TLS
(`sslmode=require`). Render Free Postgres expires after **30 days** and has no
backups; use it only for the temporary company demo. The instance created for this
work expires December 14, 2026. No paid database or automatic upgrade is configured.

“Try as a student” creates an anonymous identity with an opaque HttpOnly cookie.
Drafts, selected exercise, attempts, feedback, hint levels, completion and ordered
UTC events are saved in PostgreSQL. Local browser storage also retains unsent edits
and unresolved request IDs, so retrying a lost response does not advance a hint.
Refresh restores the session. Clearing cookies starts a different identity;
cross-device login is not part of this demo. “Delete my demo data” removes the
student's persisted work; anonymous aggregate request-budget counters remain for
up to two days to prevent deletion from bypassing limits.

Each student can replay their own events. Classroom-wide replay requires
`PRACTICE_OWNER_TOKEN` in the server's secret settings; enter it only in the owner
panel, where it is kept in memory rather than local storage. No owner key means
classroom-wide replay is disabled. The exercise bank includes no real assignments
or grades, and no personal name is required.

Checks return `correct`, `incorrect`, `needs_clarification`, or `unavailable`.
Bounded arithmetic accepts equivalent values, calculations and explicit units.
The straight-line LC-3 subset is ADD/AND/NOT, at most eight instructions, with
16-bit symbolic proof over **all** initial register values. Unsupported syntax or
an inconclusive solver produces clarification; nothing is passed to a shell,
compiler, Python eval, or arbitrary-code runner. Correct final values with
contradictory/unclear reasoning are not endorsed as complete solutions. Exercises
explicitly asking for reasoning require it before completion.

Written reasoning uses a source-grounded, criterion-level Groq assessment. Student
quotations and citation membership are validated server-side, but semantic model
judgments can still be mistaken. A misconception needs actual submitted evidence;
a wrong final value alone yields a clarifying question. Supported arithmetic errors
are checked in order, including fixed-width wraparound where appropriate. Retrieved
source text is stored with the feedback/hint so replay does not change after a model
or corpus update. Reviewed hints progress from a question to a relation to an
intermediate step without disclosing the exercise's final answer.

The inference budget is 12 practice actions per student per minute and 60 globally
per minute across server instances. Session creation is limited to 1,000 per hour.
Retries with the same request ID do not spend another action or advance hints.
Interrupted actions become recoverable after 90 seconds. Same-origin writes,
request-size limits and ownership checks protect the practice API.

Run all integration tests with a dedicated test PostgreSQL URL:

```sh
TEST_DATABASE_URL='postgresql://postgres:local-demo-only@127.0.0.1:5432/backbone' \
  python -m pytest website/backend/tests scripts/tests -q
node --test website/site/tests/*.test.mjs
```

Each database test creates and removes its own schema. GitHub CI supplies a
PostgreSQL 17 service, so these tests run there rather than being silently skipped.
A local run without `TEST_DATABASE_URL` skips database cases and is insufficient
to verify persistence. Keep production database secrets out of test commands.
