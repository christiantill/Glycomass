# VPS deployment (netcup)

The maintainer provisioned a netcup x86-64 server with 8 GB RAM and approximately
250 GB disk, running Debian 13 minimal. The live site now uses `glycomass.com` and `www.glycomass.com`;
`staging.glycomass.com` is an alias of the same app, not an isolated preview.
The former Heroku app has been deleted. The deployment can also run on other
Docker-capable VPS providers.

## Architecture

One non-root Python image runs web and worker roles on the same server. Kamal
provides TLS; PostgreSQL and Redis are accessories without published host ports.
Both application roles share `/var/lib/glycomass/files`. Only the rewrite is
copied into the image; legacy code, Git history, and local secrets are excluded.

## Local container verification

Run from the repository root. The subshell removes the disposable stack and
its volumes on success or failure:

```sh
(
  set -eu
  trap 'docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml down -v' EXIT
  docker build -t glycomass:deployment-test .
  docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml up -d --wait
  docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml exec -T web \
    python - http://localhost:8000 < deploy/smoke.py
)
```

The smoke stack uses disposable development credentials and no published ports.
Production does not use that Compose file. The test creates permalinks, an
identifier job, and files; removing this stack's volumes removes those artifacts.
Do not run this write-producing test against live or shared staging without a
separate artifact-cleanup mechanism.

## Server setup and first deployment

1. Create the server with an SSH public key. Allow inbound 80/443 and restrict SSH
   to administrator addresses using the provider firewall.
2. Create the shared file directory on the host:
   `install -d -o 10001 -g 10001 -m 0750 /var/lib/glycomass/files`.
3. Choose a staging hostname (for example `staging.glycomass.com`) and point it
   at the server. TLS needs working DNS before the deployment can finish.
4. Install Kamal 2.12.0 (`gem install kamal -v 2.12.0`) on the deploy machine.
5. Export these deployment settings:
   - `GLYCOMASS_IMAGE=christiantill/glycomass` (GHCR namespace/image)
   - `GLYCOMASS_DEPLOY_HOST` (server IP/SSH hostname)
   - `GLYCOMASS_DEPLOY_DOMAIN` (hostname, or comma-separated hostnames for the same app)
   - `KAMAL_REGISTRY_USERNAME` (GitHub account with package access)
   - `GLYCOMASS_DEPLOY_USER` (defaults to root)
6. Supply `KAMAL_REGISTRY_PASSWORD`, a fresh `POSTGRES_PASSWORD`, and
   `GLYCOMASS_DATABASE_URL` through your deployment shell or secret manager.
   The DB URL has the form
   `postgresql+asyncpg://glycomass:<URL-encoded-password>@glycomass-postgres:5432/glycomass`.
   Use a URL-safe generated password or encode it correctly. Do not paste tokens
   into chat or commit them. Copy `.kamal/secrets.example` to `.kamal/secrets`.
7. Inspect `kamal config` locally (its output may contain secrets), then run
   `kamal setup` for the first deployment and `kamal deploy` for later releases.
   Commit the intended revision first: Kamal normally builds the Git checkout.

The web entrypoint applies Alembic migrations before listening. This assumes one
web role on one host and additive, backward-compatible migrations. Do not scale
web replicas or add destructive migrations without revising migration handling.
The worker must only consume jobs after the initial schema is ready; verify web
startup before submitting the first upload. Redis is private to the Docker
network, which must not contain untrusted workloads.
Uvicorn trusts forwarded headers from that network so generated asset URLs use
HTTPS behind kamal-proxy. Do not publish port 8000 directly on the host.

## Operations

- Before deployment, use the isolated smoke flow above for calculators, saved
  links, and upload → worker → download processing. After deployment, check
  `curl --fail https://glycomass.com/api/v1/health` and load the calculator pages
  without submitting forms. These read-only checks do not validate the live
  worker pipeline.
- Browser regressions live in `tests/browser/check-spectra.cjs`; JavaScript unit
  checks run with `node --test tests/browser/spectrum-paths.cjs`.
- Completed results have no automatic expiry. Monitor disk usage; retention
  is a follow-up, not an enabled feature.
- A one-off PostgreSQL/file backup was saved on the maintainer's computer and
  restored successfully into a disposable database. Recurring/cloud backups
  were explicitly deferred by the owner for this hobby deployment. Data created
  since that backup can be lost; this is not recurring recovery protection.
  Back up both the database and shared files before risky changes.
- Deployments are manual. Merging a PR does not deploy it.
- Roll back application releases with Kamal; Heroku is no longer available.

Kamal application rollback changes the image; it does not undo migrations or
restore lost data. Keep migrations compatible with the previous image. Do not
delete accessory storage during application rollback.

## Slow-operation logs

See [performance timings](../docs/performance.md) for
algorithm costs, workload fields, thresholds, and initial measurements. Web and
worker containers warn when an instrumented phase takes at least one second.

## Current live hostnames

For this existing service, deploy with:
`GLYCOMASS_DEPLOY_DOMAIN=glycomass.com,www.glycomass.com,staging.glycomass.com`.
All three names route to the same web/worker/database deployment. Changes deployed
here affect the live site; an isolated preview would require a separate service.

## DNS

Namecheap manages the live domain. The current web records are:

| Type | Host | Value |
| --- | --- | --- |
| A | @ | 62.83.18.172 |
| CNAME | www | glycomass.com |
| A | staging | 62.83.18.172 |

Kamal manages HTTPS certificates for all three hostnames. Preserve Zoho MX and
mail/verification TXT records when changing web DNS.
