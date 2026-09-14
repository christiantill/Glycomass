# Public release checklist

As of 2026-09-14, the application is live on netcup and the repository is private.

## Prepared

- Apache 2.0 license and copyright notices; vendored libraries retain their licenses.
- `CITATION.cff` credits Melissa Bärenfänger (ORCID 0000-0002-2855-924X)
  and Christian Till. Citation is requested, not a condition added to the license.
- Branch history was cleaned and scanned for the known exposed values.
- GitHub Support purged unreferenced commits. Authenticated verification on
  2026-09-14 could no longer resolve the old commit; PRs #1–#4 and their head
  references were gone. Merged PR #5 remained.

## Before publication

- Confirm the historical AWS credentials were revoked and the leaked Flask
  secret replaced wherever used. History cleanup does not revoke credentials.
- Confirm rights to license contributed code and legacy artwork.
- Re-scan the release tree and fetched refs; review issues, PRs, Actions artifacts,
  and other GitHub surfaces for private information before changing visibility.
- Keep private rollback bundles outside Git; old clones must not reintroduce
  removed history.

## Release

Change repository visibility after the remaining checks, tag the reviewed version,
and archive the software release to obtain a DOI. Update `CITATION.cff` with the
actual version, date, and DOI. No DOI has been assigned yet. Users of the hosted
service should record their access date as well as the software citation.
