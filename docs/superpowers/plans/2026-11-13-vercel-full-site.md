# Entire site on Vercel

**Goal:** Host the existing public website and study API in the current Vercel project, with a backbone-study.vercel.app production alias if available. Remove Cloudflare from ongoing deployments. Keep old hosting recoverable.

**Architecture:** Build the existing browser assets into website/public. A public FastAPI entrypoint reuses the existing authenticated API in the same process: its bounded same-origin chat gateway injects the existing server token, and its status route reports course readiness. Vercel serves only explicitly built browser assets from its CDN. Private corpora and credentials stay server-side.

- [ ] Add tests for anonymous chat, status, validation, bounded streaming bodies and private-file isolation.
- [ ] Add public ASGI gateway and static asset build; retain authenticated backend entrypoint for compatibility.
- [ ] Update CI to deploy tested assets and backend together to Vercel, assign public alias and smoke-test both courses and followups.
- [ ] Update docs and GitHub website link; run tests and independent review; merge and verify production deployment.
