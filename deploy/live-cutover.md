# Live-domain cutover — 2026-09-14

The netcup deployment now serves https://glycomass.com and
https://www.glycomass.com using application image revision `e214631`.
`staging.glycomass.com` remains an alias of this same application.

## Current Namecheap web records

| Type | Host | Value |
| --- | --- | --- |
| A | @ | 62.83.18.172 |
| CNAME | www | glycomass.com |
| A | staging | 62.83.18.172 |

The old Namecheap www URL redirect was removed. MX and TXT records were kept;
Zoho MX routing was checked after the change. Authoritative web-record TTLs
were approximately 30 minutes when verified, so cached old answers can persist.

Both live hostnames passed certificate verification and HTTP-to-HTTPS checks.
The root live hostname passed the full calculation/permalink/identifier smoke
and browser spectrum/export/loading-state checks.

## Rollback while Heroku remains available

Restore these previous Namecheap web records if required:

| Type | Host | Value | Previous TTL |
| --- | --- | --- | --- |
| ALIAS | @ | evening-parsnip-wco91p4b87fd36xx11unmc8d.herokudns.com. | 5 min |
| CNAME | www | fundamental-carp-eqkcygg01kla6u6uovnemk5s.herokudns.com. | Automatic |
| URL Redirect (301) | www | https://glycomass.com | — |

Replace the netcup @ A record with the former ALIAS; change the www CNAME back.
The redirect row above records the previous setup exactly. Leave mail/TXT and
staging records alone. DNS rollback is subject to caching. Heroku was not shut
down or deleted, and its GitHub autodeploy remains disabled per the owner.

A pre-cutover PostgreSQL/file backup exists on the maintainer’s computer and
was successfully restored into a disposable database. No recurring/cloud backup
service was added, as requested.
