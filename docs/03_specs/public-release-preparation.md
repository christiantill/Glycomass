# Public release preparation

Status: repository is private; branch history cleanup completed 2026-09-14.

## GitHub Support cleanup verified (2026-09-14)

GitHub Support confirmed that unreferenced commits were cleared. Authenticated
verification found that the commits API no longer resolves the old commit
`2d24f0ad94f5b8dd3eeabe6ac93a5affe2832ef3` (HTTP 422, "No commit found").
The all-state PR listing contains only merged PR #5, and `git ls-remote` exposes
only `refs/pull/5/head`; PR #1–#4 head references are gone.

This completes the hosted-history cleanup step described below. Confirmation
that the historical AWS credentials and Flask secret were revoked/replaced is
still pending. Repository visibility remains private.

## Completed in the rewrite PR

- Rewrite phases 0–4 pushed for review.
- Validation before publication preparation: 110 default tests, 795 grid parity
  tests, 97.05% coverage, ruff, mypy, and lockfile checks passed.
- Legacy config now reads `SECRET_KEY`, `S3_BUCKET`, `S3_KEY`, and `S3_SECRET`
  from environment variables. A legacy deployment must set `SECRET_KEY` before
  using this revision; the unsafe fallback has been removed.
- Tracked Python bytecode and IDE configuration removed from the current tree.
- Environment example and broader secret-file ignores added.
- Software citation prepared with the authors credited on the original About
  page and Melissa's ORCID supplied by the maintainer. No DOI is invented.
- Citation CFF 1.2.0 schema validation and citation page/footer smoke passed.
- Gitleaks scan of current tracked/new source files passed after cleanup.
- Upstream license texts included for vendored HTMX 2.0.3 and uPlot 1.6.32.

## Credentials and history: outstanding

Gitleaks 8.30.1 scanned all fetched Git refs (164 commits) and reported an AWS
access token in historical `config.py`. Manual inspection also found a hardcoded
Flask secret and an AWS secret-shaped value used incorrectly as an environment
variable name. Credential validity was not tested. No secret values are included
in this report. A clean current-tree scan does not clear historical exposure.

1. Revoke/rotate the old AWS credentials and Flask secret with their providers.
   Confirm revocation; removing text from Git does not revoke credentials.
2. Decide whether to retain history after confirmed revocation or purge the old
   values. If purging, rehearse `git-filter-repo` in a separate mirror, replacing
   credential strings and dropping historical bytecode. Review every branch,
   including `Stable`, `milz`, `master`, and the rewrite branch, and all tags.
3. Coordinate any remote history rewrite after PR review: commit hashes change,
   existing clones can reintroduce secrets, and GitHub PR/cached references may
   retain old objects. Do not blindly force-push the working repository.
4. Review GitHub issues/PRs, Actions logs/artifacts, releases, and any wiki for
   sensitive information; the Git scan does not cover those surfaces.
5. Re-scan the intended public state, then change repository visibility once
   the outstanding release decisions are resolved.

Follow [GitHub's sensitive-data removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
After the maintainer confirmed Heroku autodeploy was disabled, all four remote
branches were replaced atomically with cleaned history using explicit commit
leases. Five legacy credential values were removed, historical config now uses
environment variables, and bytecode/IDE files were removed across history.
The rewritten history passed Gitleaks and an exact search for the known values.
The rewrite branch's latest file tree was identical before and after cleanup.
This checkout was synchronized and its old reflogs/objects pruned.

GitHub-managed PR references/cached commits are separate from branch history and
can retain old objects. Resolve those references with GitHub Support where
necessary before treating the entire hosted repository as clean. Credential
rotation and repository visibility change have not been performed. A restricted
local rollback bundle is retained outside the repository; it contains old history
and must never be published. Other clones should be replaced or carefully cleaned
to prevent reintroducing old commits.

## Citation and licensing

The maintainer wants software citation, with Melissa Bärenfänger's ORCID
0000-0002-2855-924X. Author order follows the original About page. Record a real
software DOI, version, and release date after publishing an archived release.

The maintainer selected Apache 2.0, including for future monetization and support.
Copyright attribution is recorded in `NOTICE`, which is included in source, Python
packages, and container distributions. Citation remains a scholarly request;
the standard license does not require paper citations. Confirm rights to license contributions and legacy
artwork before release; vendored dependencies retain their own licenses.

[GitHub citation files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
enable the citation button once the file is on the default branch.

## Hosting migration

The existing design spec targets Heroku → netcup with Kamal. This fits the
existing web/worker design: both processes need access to the same upload/result
files, alongside PostgreSQL and Redis.

Render is a managed alternative, but its disks cannot be shared across services.
Separate web and worker services would need shared object storage or a different
file-transfer design: [Render disk limitations](https://render.com/docs/disks#disk-limitations-and-considerations).

Docker/Kamal configuration and a disposable local integration stack are now in
`deploy/`; see its README. The image build, Kamal 2.12.0 configuration check, and
real PostgreSQL/Redis/worker integration smoke passed, including saved permalinks
and upload-to-download processing. Still needed on the actual server: upload/result
retention, backup/restore verification, and production domain cutover with a
rollback path. The provisioned server runs Debian 13 with key-only SSH and HTTPS staging. The maintainer selected netcup/self-managed hosting.
The netcup server is provisioned and staging is live at https://staging.glycomass.com.
See `deploy/staging-status.md` for current deployment validation; production cutover
and scheduled backups/retention remain outstanding.

## Review follow-up (2026-09-14)

Codex review findings on PR #5 were addressed before the next CodeRabbit review:
MGF peak matching now uses linear memory; uploads are bounded while streaming;
identifier processing runs in a cancellable child process with one active job;
source uploads are removed only after committing successful results. Legacy
calculator/identifier bookmarks redirect permanently, and both peracetyl spellings
produce the same permalink and selected form option.

Protein calculations now reject negative disulfide counts and counts requiring
more cysteines than the sequence contains. This intentionally differs from legacy
fixtures that subtracted hydrogen for impossible bridges. Those fixtures assert
validation errors; numerical tolerances for valid calculations are unchanged.

Validation: 125 default tests (96% coverage), 795 grid cases, Ruff, strict mypy,
and the frozen dependency lock check pass.
