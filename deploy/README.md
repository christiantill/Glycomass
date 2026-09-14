# VPS deployment (netcup)

The maintainer provisioned a netcup x86-64 server with 8 GB RAM and approximately
250 GB disk, running Debian 13 minimal. Initial deployment uses
`staging.glycomass.com`; the main domain remains on the existing service until
cutover. Docker officially supports Debian 13. The same deployment also works on
other Docker-capable VPS providers; it has no Hetzner-specific dependencies.

## Architecture

One non-root Python image runs web and worker roles on the same server. Kamal
provides TLS; PostgreSQL and Redis are accessories without published host ports.
Both application roles share `/var/lib/glycomass/files`. Only the rewrite is
copied into the image; legacy code, Git history, and local secrets are excluded.

## Local container verification

```sh
docker build -t glycomass:deployment-test .
docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml up -d --wait
docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml logs worker
# Remove only this disposable smoke stack and its test data:
docker compose -p glycomass-deploy-smoke -f deploy/compose.smoke.yml down -v
```

The smoke stack uses disposable development credentials and no published ports.
Production does not use that Compose file.

## Server setup and first deployment

1. Create the server with an SSH public key. Allow inbound 80/443 and restrict SSH
   to administrator addresses using the provider firewall. Enable server backups.
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

## Before production cutover

- Verify all calculators, a saved permalink after restart, and a real upload →
  worker → download flow on staging. Load-test representative MGF sizes.
- Implement a result/upload retention policy and monitoring for disk growth;
  completed result files currently have no automatic expiry.
- Schedule encrypted off-server PostgreSQL logical backups and file backups,
  and restore them on a disposable database/server. Server snapshots alone are
  not a tested database backup strategy. Permalinks need durable DB backups.
- Add deployment CI and a dedicated deploy credential after server access is
  established. This preparation does not automatically deploy on merge.
- Before changing production DNS, record existing records, lower TTL, test TLS,
  and establish a rollback window. Keep Heroku available through that window;
  disable its GitHub autodeploy before replacing repository history.

Kamal application rollback changes the image; it does not undo migrations or
restore lost data. Keep migrations compatible with the previous image. Do not
delete accessory storage during application rollback.

## Slow-operation logs

See [performance timings](../docs/03_specs/performance-observability.md) for
algorithm costs, workload fields, thresholds, and initial measurements. Web and
worker containers warn when an instrumented phase takes at least one second.
