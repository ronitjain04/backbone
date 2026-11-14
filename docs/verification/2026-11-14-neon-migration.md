# Backbone practice database migration to Neon Free

Date: November 14, 2026. User requested migration from Render to Neon Free.

## Resources and preserved data

- Neon project: `backbone-practice` (`holy-paper-16977739`), production branch `br-lively-scene-bbqhyxcw`, PostgreSQL 17, AWS Virginia.
- Confirmed organization plan: `free_v3`. Scale-to-zero uses the free plan's default inactivity timeout. No paid services, payment details, or automatic upgrade were configured.
- Source: Render `backbone-practice-demo` (`dpg-dbsa02gae00c73d0fsqg-a`). It remains readable as a rollback copy until its December 14 expiration.
- Copied all 11 application tables over TLS with PostgreSQL COPY, preserving UUIDs, bank versions, token digests, timestamps, JSONB feedback and replay events.
- Verified matching row counts and SHA-256 fingerprints of canonical JSON records. Canonical serialization avoids JSON formatting/order differences between database implementations.

| Table | Rows at cutover |
| --- | ---: |
| classrooms | 1 |
| students | 5 |
| memberships | 5 |
| exercises and follow-ups | 36 |
| sessions | 5 |
| progress | 7 |
| submissions | 10 |
| feedback | 6 |
| hints | 4 |
| events | 37 |
| aggregate budget buckets | 7 |

Private COPY exports and the detailed verification manifest are stored outside Git with a mode-700 directory and mode-600 data files. Connection credentials are never included in documentation, logs, or browser assets.

## Cutover and authorization

An initial automatic approval review rejected persisting a read-only setting on Render because its exact scope and rollback timing had not been explicitly approved. No source-role change occurred from that rejected command. The data was first copied and verified with Render's role unchanged.

The user subsequently explicitly approved making the old Render database role read-only after transfer, blocking writes from older review deployments while retaining readable data until December 14, with writes restorable for rollback. Applied that exact setting and reverified the final source/target fingerprints before switching Vercel's production `DATABASE_URL` Secret to Neon.

Existing deployments retain their original environment snapshots. Use the newest review deployment for Neon writes; legacy review URLs continue to read the Render snapshot. The existing public domain remains on its previous release until the practice PR is merged. No main-branch merge or public-domain reassignment is part of this migration.

## Connection compatibility and verification

- Preserved FastAPI and psycopg; no application schema or model-provider changes.
- Use the direct Neon connection. Its pooled URL rejects the application's startup `statement_timeout` option. The direct URL passed an actual Store workflow: create a temporary student, save a draft, restore it and read ordered replay events. The temporary student was deleted, then the final snapshot was refreshed so validation writes were excluded from the cutover data.
- The bundled local PostgreSQL command-line tools lacked TLS support, so the transfer used psycopg's TLS-enabled COPY protocol instead of an insecure connection or disabled TLS validation.
- Vercel stores the Neon URL as a Secret, with TLS required. The existing owner replay credential remains unchanged.
- Hosted workflow verification is recorded below after deployment.

## Rollback

Restore the Render connection from its console and reset the original app role's `default_transaction_read_only` setting using a session configured with `default_transaction_read_only=off`. Restore Vercel's `DATABASE_URL` Secret and redeploy a verified app revision. If Neon has accepted new student work, export/reconcile it before rollback; the original Render snapshot does not contain post-cutover Neon changes. Do not delete either database or overwrite new work as part of rollback without reviewing the data first.
