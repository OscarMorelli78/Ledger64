# Docker deployment and acceptance
Run the Container acceptance workflow and review both application and proxy vulnerability scans. Docker Compose uses Traefik v3.8.0 for HTTPS, request limits and host routing without access to the Docker socket. Set BC_DOMAIN to a real domain you control and optionally BC_ACME_EMAIL for certificate contact. See [RELEASE.md](RELEASE.md) for deployment instructions. CI uses a local test certificate, not a public ACME certificate. No production credentials or real invoices are included. Synthetic data only until deployment-specific security, privacy, backups and real-data validation pass. Do not remove business_data when migrating from Caddy.

## Local procurement pilot

Use branch `feat/adaptive-procurement-v1`, Python 3.13 and the local loopback quick start from the [manual](docs/manual/en.md#14-procurement-intelligence--experimental-pilot). Set `BC_PROCUREMENT_PILOT=1` before starting the server; login at /login then visit /procurement. Distinct analyst and owner required. The flag is off by default. Synthetic data only. Container validation is not authorization for real data or a public deployment. [Recovery](docs/procurement-data-resilience.md).

GitHub Pages only hosts static demos. GitHub Actions validates a temporary backend and produces a source snapshot; it is not persistent application hosting. Do not expose a public backend or add paid infrastructure without separate approval.
