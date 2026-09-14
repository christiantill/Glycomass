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
- Until DNS is ready, `glycomass-preview-web` listens only on host loopback
  `127.0.0.1:18000`; `glycomass-preview-worker` processes its jobs. Both mount
  `/var/lib/glycomass/files`, using a root-readable environment file outside Git.
- End-to-end synthetic smoke covers health, citation, all calculators, saved
  permalinks, Redis queue, worker processing, and result download. Proxy scheme
  handling was checked so static asset links use HTTPS behind the TLS proxy.

## DNS and completion

The owner selected `staging.glycomass.com`. Last DNS check returned NXDOMAIN.
Add an A record `staging` → `62.83.18.172`. No apex/www record changes are needed.
The public staging endpoint and TLS certificate are pending this record.

Once DNS resolves:

1. Stop/remove the two `glycomass-preview-*` containers (preserve accessories and
   all data directories), so only the Kamal-managed worker consumes the queue.
2. Supply deployment settings and secrets as described in `deploy/README.md`.
3. Run `kamal deploy --skip-push --version aa07bec9a6e7e5208064ceef6ccce8dbcbeab31d`
   for the existing image, or build/deploy a newer reviewed revision.
4. Run `python3 deploy/smoke.py https://staging.glycomass.com` and verify restart
   persistence before production cutover.

No live-domain cutover, repository visibility change, result-retention job,
off-server backup schedule, or deployment CI has been enabled.
