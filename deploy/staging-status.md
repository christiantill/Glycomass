# Staging provisioning status

2026-09-14: netcup host `62.83.18.172`, Debian 13, x86-64, 4 vCPU,
8 GB RAM, approximately 250 GB disk.

- SSH ED25519 host key verified against the provisioning email.
- Dedicated deployment key and owner's laptop public key installed. Initial
  root password rotated; SSH password/keyboard-interactive login disabled.
- Docker Engine 29.8.0 installed from Docker's official Debian repository and
  verified. Automatic security upgrades enabled without automatic reboot.
- Persistent host ingress rules allow SSH, HTTP/HTTPS, ICMP, and established
  traffic over IPv4/IPv6. Docker-published ports are managed separately; do not
  expose databases or the application port publicly. Provider SMTP policy was
  left unchanged.
- Kamal accessories `glycomass-postgres` and `glycomass-redis` are running on
  Docker network `kamal`, with persistent host storage and no published ports.
- Image `ghcr.io/christiantill/glycomass:aa07bec9a6e7e5208064ceef6ccce8dbcbeab31d`
  was built from the committed rewrite; registry package remains private.
- Kamal-managed web and worker roles now serve `https://staging.glycomass.com`
  through kamal-proxy. Both mount `/var/lib/glycomass/files`, using root-readable
  environment files outside Git. Temporary preview containers were removed.
- End-to-end synthetic smoke covers health, citation, all calculators, saved
  permalinks, Redis queue, worker processing, and result download. Proxy scheme
  handling was checked so static asset links use HTTPS behind the TLS proxy.

## DNS and HTTPS validation

The owner added the Namecheap A record `staging` → `62.83.18.172`.
Public DNS and the server resolver return the new IP. Some resolvers initially
retained the earlier NXDOMAIN response; no apex/www records were changed.

The deployment completed through Kamal using image revision
`aa07bec9a6e7e5208064ceef6ccce8dbcbeab31d`. HTTPS serves a valid certificate for
the staging hostname (initial certificate expires 2026-12-13); kamal-proxy manages
renewal. HTTP redirects to HTTPS.

The complete synthetic smoke passed through HTTPS from the deployment machine,
using an IP resolution override while preserving hostname/SNI and certificate
verification to bypass its stale DNS cache. Server-side HTTPS health also passed
with normal DNS. CSS and chart JavaScript returned successfully. A saved
permalink survived a web/worker restart.

For future deployments, supply settings/secrets as described in `deploy/README.md`,
run `kamal deploy`, then run
`python3 deploy/smoke.py https://staging.glycomass.com`.

No live-domain cutover, repository visibility change, result-retention job,
off-server backup schedule, or deployment CI has been enabled.
