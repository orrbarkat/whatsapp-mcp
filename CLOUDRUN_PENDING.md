# Pending work for Cloud Run hardening

This file tracks deferred items and future improvements for the Cloud Run deployment.

1) QR code surfacing for remote auth (bridge)
- Add an HTTP route to expose the current pairing QR (ASCII or PNG). This allows remote onboarding without a TTY.
- Security: protect the endpoint (require auth), short-lived tokens, and avoid logging QR contents.

2) Persistence for data (SQLite -> managed storage)
- Option A: Migrate to Cloud SQL (Postgres/MySQL). Update both Go and Python to use a proper DB instead of SQLite.
- Option B: GCS FUSE mounted volume on Cloud Run for SQLite files (messages.db, whatsapp.db). Note SQLite locking caveats and single-instance constraints.

3) CI/CD
- GitHub Actions workflow to: lint/test, build images, push to Artifact Registry, deploy to Cloud Run on main/tag.
- Cache dependencies and build layers for faster builds.

4) Observability & SRE
- Structured logs; log correlation IDs.
- Uptime checks and alerting; error reporting hooks.
- Metrics for message throughput, media download success/latency, auth status.

5) Security hardening
- Secrets in Secret Manager (e.g., any long-lived tokens if introduced).
- Least-privilege service accounts; egress restrictions.
- Narrow down who can invoke MCP and bridge services.

6) Region/cost validation
- Default region set to me-west1 (Tel Aviv). Validate against nearby EU regions for latency/cost tradeoffs.

7) Makefile / dev UX
- Optional: Make targets for docker build/test/deploy; or a tiny docker-compose for local two-service testing.
