# Backbone website

A responsive introduction and live study chat, with source excerpts. The Python API performs retrieval before asking an HTTP model provider to explain. No prepared answers replace model calls.

## Current state

The website, API, tests, original demo corpus, Dockerfile, and Render Blueprint are implemented. A hosted API and inference endpoint must be configured before live answers will work. The website explicitly displays this state. The configured readiness endpoint checks loaded resources and model settings, not model-provider reachability; verify an actual chat request before sharing a live demo.

The starter collection contains six **original demo notes**, not Georgia Tech slides or textbook excerpts. Production private course data is not included. The default demo uses lightweight lexical retrieval; optional `RETRIEVAL_MODE=semantic` uses normalized sentence embeddings and a FAISS inner-product index. The previous sibling app's API contract and grounding approach are preserved; this deployment uses explicit JSONL documents rather than runtime pickle loading.

## Local preview

From the repository root:

```sh
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

For semantic retrieval, install `backend/requirements-semantic.txt` in a suitable image and set `RETRIEVAL_MODE=semantic`. This requires more memory and a downloaded embedding model and has not been exercised by the lightweight test suite. For a private corpus, mount a UTF-8 JSONL file outside the source checkout and set `CORPUS_PATH`. Each line must have nonempty `text` and `source` strings and an optional `details` string. Split excerpts into chunks under 10,000 characters. Do not publish lecture slides, textbooks, extracted course chunks, or indexes in the frontend or source repository.

## Publish the website

`site/.openai/hosting.json` stores the exact Sites identity. `node website/site/build.mjs` generates a self-contained Worker at `site/dist/server/index.js`. Package and publish using the Sites source workflow; the website has no npm runtime dependencies. Publish only `website/site`, not this whole repository. New Sites are private by default; wider tester access must be configured with supported Sites controls.

## Verify

```sh
website/.venv/bin/pip install pytest
website/.venv/bin/python -m pytest website/backend/tests -q
node --test website/site/tests/*.test.mjs
node website/site/build.mjs
node --check website/site/dist/server/index.js
```

Before calling it a working live demo: check `/ready`, submit a real question through the published website, inspect its returned sources, and verify visitor access. Unit tests use a controlled model boundary and do not prove a hosted model is running. Inference requests send the question and retrieved excerpts to your configured model provider; configure its retention and privacy settings accordingly.
