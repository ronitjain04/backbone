# Backbone website

A responsive introduction and live study chat, with source excerpts. The Python API performs retrieval before asking an HTTP model provider to explain. No prepared answers replace model calls.

## Current state

The website and Render API are deployed and connected to Groq using GPT-OSS 20B. A complete live answer with source excerpts was verified through the published website. The website is public at [backbone-study-ronit.ronit-jain.chatgpt.site](https://backbone-study-ronit.ronit-jain.chatgpt.site). The configured readiness endpoint checks loaded resources and model settings, not provider availability or remaining quota; inference remains subject to provider limits.

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

For the website preview, set `BACKEND_URL=http://127.0.0.1:8000` and the same `BACKEND_TOKEN` as the API, then restart `node website/site/dev.mjs`. `/health` checks process liveness; `/ready` returns 503 until the corpus and model settings load and a backend token is configured. Ten chat attempts per minute per backend process limit inference traffic. Use one worker for this process-wide budget; multi-instance deployments need a shared limit. No chat history is stored server-side. Each request is independent.

## Host the backend

The Docker build context is the repository root:

```sh
docker build -f website/backend/Dockerfile -t backbone-api .
```

Connect a sanitized repository to Render and set the Blueprint Path to `website/render.yaml`, or use the Dockerfile on another compatible host. The Blueprint configures the original demo corpus and prompts for inference settings; it generates a backend token. Choose and review the hosting plan in your hosting account; no paid service has been provisioned by this project. See [Render's Blueprint reference](https://render.com/docs/blueprint-spec).

Keep `MODEL_API_KEY` and `BACKEND_TOKEN` in the host's secret manager. Configure `BACKEND_URL` and the matching `BACKEND_TOKEN` as Sites runtime environment values. Keep the backend behind TLS and the token gate. The API deliberately exposes no cross-origin browser access; browsers use the same-origin website proxy.

For semantic retrieval, install `backend/requirements-semantic.txt` in a suitable image and set `RETRIEVAL_MODE=semantic`. This requires more memory and a downloaded embedding model and has not been exercised by the lightweight test suite. For private corpora, mount UTF-8 JSONL files outside the source checkout and set `CS2110_CORPUS_PATH` and/or `CS2200_CORPUS_PATH`. The legacy `CORPUS_PATH` remains a CS 2200 fallback. Each course loads independently, so a missing CS 2110 file does not take CS 2200 offline. `/ready?course=cs2110` and `/ready?course=cs2200` report per-course configuration; `/ready` succeeds when at least one course is configured. Chat bodies accept `{ "query": "…", "course": "cs2110" }` (default course: `cs2200`). Each line must have nonempty `text` and `source` strings and an optional `details` string. Split excerpts into chunks under 10,000 characters. Do not publish lecture slides, textbooks, extracted course chunks, or indexes in the frontend or source repository.

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
