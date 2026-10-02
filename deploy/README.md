# VPS deployment

The maintainer provisioned an x86-64 VPS with 8 GB RAM and approximately
250 GB disk, running Debian 13 minimal. The live site now uses `glycomass.com` and `www.glycomass.com`;
There is no hosted staging environment; use the isolated local stack for testing.
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
Do not run this write-producing test against production without a
separate artifact-cleanup mechanism.

## Server setup and first deployment

1. Create the server with an SSH public key. Allow inbound 80/443 and restrict SSH
   to administrator addresses using the provider firewall.
2. Create the shared file directory on the host:
   `install -d -o 10001 -g 10001 -m 0750 /var/lib/glycomass/files`.
3. Choose the application hostname and point it
   at the server. TLS needs working DNS before the deployment can finish.
4. Install Kamal 2.12.0 (`gem install kamal -v 2.12.0`) on the deploy machine.
5. Export these deployment settings:
   - `GLYCOMASS_IMAGE=christiantill/glycomass-app` (GHCR namespace/image)
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
- Application/deployment changes merged to `master` deploy through GitHub Actions
  after tests pass. Documentation-only changes skip deployment.
- Roll back application releases with Kamal; Heroku is no longer available.

Kamal application rollback changes the image; it does not undo migrations or
restore lost data. Keep migrations compatible with the previous image. Do not
delete accessory storage during application rollback.

## Memory and CPU limits

The server (4 vCPU, 8 GB RAM, 2 GB swap) also runs other services with their own
limits. Glycomass is a small hobby service, so `config/deploy.yml` keeps it to a
small share of the host, and a runaway job fails inside its own container instead
of starving the host:

| Container | Memory | + swap | CPUs | Basis |
| --- | --- | --- | --- | --- |
| web | 512m | 128m | 0.5 | 108 MiB in production; uploads stream to disk: a 250 MB upload took 6 s and peaked at 100 MiB of process memory (the kernel reclaims the upload's page cache at the cap); a 100,000-residue super-high protein calculation peaks at 54 MiB |
| worker | 1g | 256m | 1.0 | 61 MiB idle in production; one job at a time; the single-threaded identifier child stays near 150 MiB for 250 MB uploads of ordinary spectra |
| postgres | 512m | 128m | 0.5 | 106 MiB in production; default `shared_buffers` (128 MB) |
| redis | 128m | 32m | 0.25 | 9 MiB in production; arq queue only, so no eviction policy |

Swap is a quarter of each memory cap. Production figures are `docker stats` on
2026-10-02; the rest are local runs of the production image on 2026-10-02 with
these limits applied.

The identifier reads, filters and writes one spectrum at a time, so its memory no
longer grows with the file. Peak RSS of the identifier child for 250 MB synthetic
uploads in which every spectrum is selected and written:

| Upload | Before (whole file in memory) | Streaming |
| --- | --- | --- |
| 37,000 spectra of 400 peaks | 868 MiB | 153 MiB |
| 940,000 spectra of 11 peaks | 3.1 GiB | 68 MiB |

The 250 MB upload limit therefore stays. Memory now depends on the largest single
spectrum instead: about 11 times its text size (a 50 MB spectrum of 2.5 million
peaks peaked at 568 MiB). A spectrum above roughly 80 MB exceeds the worker cap;
real MS/MS spectra are far below that.

Failures stay inside the job. The identifier child sets its OOM score so the
kernel kills the child, not the arq parent: a 250 MB single-spectrum upload
failed with "Processing ran out of memory" and the worker then processed the
next job. A file of about a million tiny spectra takes over 5 minutes on one CPU
and fails on arq's 5-minute job timeout ("Processing was cancelled or timed
out"). Either way the partial result is removed, and failed jobs are not retried.

Role caps apply on the next deploy. Accessory options apply only when the
accessory container is recreated; `kamal deploy` does not touch running
accessories. With the deployment environment set (see Kamal setup above), and
while no identifier job is running:

```sh
kamal accessory reboot redis     # queue is restored from its append-only file
kamal accessory reboot postgres  # web requests fail for a few seconds
kamal app boot                   # replaces web and worker containers: fresh DB pools
```

The app boot is required after a Postgres reboot: the connection pools do not
check connections before reuse, so a stale connection would fail the next job
before it can record its status. For an already running version, Kamal renames
the current containers, starts new ones, then stops the old ones.

Then check the limits with `docker stats --no-stream` on the server, the health
endpoint, and `kamal app logs -r worker` for a reconnected worker.

## Slow-operation logs

See [performance timings](../docs/performance.md) for
algorithm costs, workload fields, thresholds, and initial measurements. Web and
worker containers warn when an instrumented phase takes at least one second.

## Current live hostnames

For this existing service, deploy with:
`GLYCOMASS_DEPLOY_DOMAIN=glycomass.com,www.glycomass.com`.
Both names route to the same web/worker/database deployment. Changes deployed
here affect the live site; an isolated preview would require a separate service.

## DNS

Namecheap manages the live domain. The current web records are:

| Type | Host | Value |
| --- | --- | --- |
| A | @ | the server's public IPv4 address |
| CNAME | www | glycomass.com |

Kamal manages HTTPS certificates for both hostnames. Preserve Zoho MX and
mail/verification TXT records when changing web DNS.

## Automatic deployment

`.github/workflows/ci-deploy.yml` tests every PR without deployment credentials.
Application/deployment changes pushed to `master` run the same checks, then Kamal
builds and deploys that tested commit. Only one master workflow runs at a time;
running deployments are not cancelled by newer pushes. Superseded revisions are
skipped before deployment setup. Do not run manual Kamal deployments concurrently
with Actions; they use the same service and deployment lock.

GitHub Actions → **Test and deploy** → **Run workflow** on `master` also runs tests
and deploys, even without code changes. Selecting another branch never deploys.
Kamal switches web traffic after its health check passes; a final read-only HTTPS
check verifies the public endpoint. Failures appear in Actions. This is not an
automatic database rollback or a full live worker smoke test.

Repository Actions secrets:

- `DEPLOY_SSH_KEY`: dedicated deployment private key authorized on the server.
- `DEPLOY_KNOWN_HOSTS`: verified server SSH host-key entry.
- `POSTGRES_PASSWORD`: existing production database password.
- `GLYCOMASS_DATABASE_URL`: existing production database URL.

GHCR authentication uses the workflow's temporary `GITHUB_TOKEN` with package
write access. The `glycomass-app` package is created by this workflow and linked to the
repository. The older manually published `glycomass` package is retained for
rollback but is no longer used for new deployments.
Never use `pull_request_target` to execute untrusted PR code with these secrets.

## Another app on the same server

Keep the Dockerfile, `config/deploy.yml`, secrets, and workflow in that app's own
repository. Choose a unique Kamal service name and image, a separate hostname,
and separate database credentials and storage paths. Point its DNS to the same
server; the existing Kamal proxy handles domain routing and HTTPS for each app.
Do not copy Glycomass's database URL, file volume, or hostnames into another app.

There is no shared package to publish. Reuse this small configuration as a
starting point and maintain it per app. Apps share host resources and the Docker
network; this is suitable for the owner's trusted apps, not untrusted tenants.

The former `staging` A record should be removed from Namecheap; the deployment
no longer routes that hostname.
