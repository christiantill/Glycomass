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
- Image `ghcr.io/christiantill/glycomass:adcea072b73e5ee2a6e1fe3fd8703e1652f852e2`
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
`adcea072b73e5ee2a6e1fe3fd8703e1652f852e2`. HTTPS serves a valid certificate for
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

## Review fixes deployed

Revision `2e26dd0` addresses the seven Codex review findings. Both web and worker
roles run the deployed image listed above. The complete synthetic smoke passed again from the server
using normal DNS and from the deployment machine using the IP override with TLS
verification. Legacy URL redirects and invalid disulfide API rejection also passed
over HTTPS.

## Apache 2.0 release packaging

The licensing commit and its descendants were rewritten to use Apache 2.0.
The currently deployed image includes the standard LICENSE and an attribution
NOTICE naming Melissa Bärenfänger and Christian Till. Its installed package
metadata declares `Apache-2.0`. Wheel/source archive contents were verified,
and the complete HTTPS deployment smoke passed after this image was deployed.

## Performance instrumentation

Revision `aea063a` adds configurable slow-operation timings. Calculator and
child-process phase events were verified in the deployed image; a real queued
synthetic job produced a 1306 ms warning in the worker's Docker logs. Complete
HTTPS smoke passed with the instrumented web and worker roles.

## Second review follow-up

Revision `fa6e167` enforces calculator body/sequence limits, records cancelled
jobs as failed, cleans up failed upload persistence, rejects unrecognizable MGF
uploads, serializes lazy Redis initialization, and fixes form error rendering and
accessible labels. Both roles run this revision. Full HTTPS smoke and staging
rejection checks for overlong protein sequences and empty MGF files passed.

## Navigation and spectrum verification

Revision `4004835` includes the calculator navigation and sampled Gaussian profile
repair. Chromium checks passed on staging for all three calculators, Profile/Peaks
switching, repeat submissions and mobile resizing. The server-side HTTPS smoke
passed for calculators, saved results and queued identifier processing. See
`docs/03_specs/engine-reference-audit.md` for the separate repository comparison
and inherited engine behaviors that still need scientific/input validation.

## Spectrum transfer and progress correction

Revision `cced508` defaults to zero-baseline sticks and adds immediate calculation
status with duplicate-submit protection. Rounded HTML profile data and gzip
reduced the default glycan transfer from 464,868 to 35,035 bytes. A measured
staging request completed in 0.55 seconds versus 12.05 seconds before this fix
(network timings are observations, not a latency guarantee). Staging Chromium
checks verified actual peak/gap pixels, progress while a response is delayed,
button recovery, toggles, repeated calculation and mobile layout. HTTPS smoke
passed again. Changed asset URLs are versioned for normal reloads.

## Expanded labels and requested Profile default

Revision `4bb3087` expands sugar field labels with abbreviations in parentheses,
uses readable sentence-case labels and adapts narrow forms to a single column.
Profile is the default again at the owner's request; Peaks remains available.
Staging browser checks passed for labels at 1440/390/320px and for the initial
Profile data, alternate peak strokes, loading status and compressed responses.

## Peak annotations and data exports

Revision `adcea07` adds collision-aware m/z annotations, a label toggle and zoom
reset, plus a collapsible discrete peak table, minor-peak visibility control,
clipboard TSV and CSV download. Profile remains the initial view. The staging
browser suite passed for all calculators, including label boxes/zoom, table rows,
clipboard contents, downloaded CSV, progress, repeat calculations and mobile
layout. The default glycan compressed response is approximately 36 KB.
