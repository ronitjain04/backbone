# Vercel backend migration plan

Goal: replace Render with Vercel Hobby while keeping the Cloudflare public address and the passing-test daily deployment gate.

Approach selected by Ronit: reuse the FastAPI backend as a Vercel function. Store the private CS 2110 corpus in a private Blob store, load it into memory at startup, and keep model/service credentials in encrypted Vercel settings. No course content or credentials enter the public repository or frontend bundle. Python 3.12 is the Vercel runtime.

- [ ] Add bounded, authenticated private Blob corpus loading with regression tests
- [ ] Add Vercel entrypoint/configuration and release metadata; test startup and both course APIs
- [ ] Change GitHub Actions to deploy the tested backend to Vercel before publishing Cloudflare; preserve PR isolation, daily schedule and public smoke tests
- [ ] Provision free Vercel project/store, transfer approved secrets/data, validate live answers and startup timing
- [ ] Independently review changes, pass GitHub CI, merge and verify full production deployment; retain Render for rollback
