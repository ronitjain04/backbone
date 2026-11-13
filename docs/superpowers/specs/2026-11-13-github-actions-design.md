# GitHub Actions design

Approved by Ronit on 2026-11-13.

Run frontend and backend tests on pushes and pull requests. On main, after both pass, deploy the tested commit to Render and Cloudflare Pages. Repeat daily at 09:17 UTC and allow manual runs. Verify the backend commit, both course readiness endpoints, and public live answers after deployment. Use existing hosts and private corpus settings; credentials stay in GitHub secrets. Deployment must never run for pull requests or non-main branches.

## Approaches
GitHub Actions was selected to put testing, daily deployment and run logs together in the repository. Host-only auto deployment would not coordinate both services or enforce the complete test gate. A daily schedule plus main pushes avoids waiting for a timer after merging changes.
