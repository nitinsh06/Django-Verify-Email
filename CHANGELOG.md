# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [3.1.0]

This is a backwards-compatible maintenance release. Public imports, URL names,
template paths and settings names are unchanged.

### Security
- **Account-enumeration fix.** The public "request a new verification email"
  form now returns an identical response whether or not the submitted address
  belongs to a real account, and regardless of whether that account is already
  active. Previously it returned a `404 "User Not Found"`, an "Already Verified"
  page, or a success page depending on the account's state, which let anyone
  probe which emails were registered and their status.
- The verification view no longer surfaces internal error details unless the
  project is running with `DEBUG = True`.
- **Already-active accounts are no longer re-activated.** The activation path now
  explicitly refuses an already-active account (raising `UserAlreadyActive` and
  showing an "already verified" page) instead of resetting `last_login`. The
  token check already covered the normal case; this is defense-in-depth for
  accounts activated out-of-band.
- Documented operational hardening in the README (bounding the resend window via
  `PASSWORD_RESET_TIMEOUT`, and adding IP-based throttling) following a security
  audit of the verification flow.

### Fixed
- **Restored the documented public API.** `send_verification_email(request, form)`
  — the entry point shown in the README/quick-start — no longer existed after the
  3.0 refactor; calling it raised `ImportError`. It is back as a thin wrapper over
  `ActivationMailManager.send_verification_link` and is importable both from
  `verify_email` and `verify_email.email_handler`. Covered by a regression test.
- The verification link is now built with `reverse('verify-email', ...)` instead
  of a hard-coded `/verification/` path, so mounting `verify_email.urls` under any
  prefix works correctly.
- `TokenManager.get_user_by_token` could raise `InvalidToken` after checking only
  the first user when multiple accounts shared an email address. It now checks
  every candidate before deciding the token is invalid.
- Removed unreachable/incorrect branches in `TokenManager._get_seconds` (a code
  path returned a `WrongTimeInterval` instance instead of raising it).
- `GetFieldFromSettings.get` had a dead guard that meant `raise_exception` never
  fired; it now correctly raises when a required setting resolves to `None`.

### Changed
- **No more global user signal.** Previous versions registered a `post_save`
  handler on the project's user model that created a `LinkCounter` row for
  *every* user (and re-saved it on every user save). This polluted the database
  and added a query to every user save in the host project. The signal has been
  removed; the counter is now created lazily the first time a user requests a
  resend. **No migration or data change is required** — existing `LinkCounter`
  rows are reused untouched, and resend-limit behaviour is unchanged.
- **Namespaced the base template.** The shared base template moved from the
  un-namespaced `email_index.html` to `verify_email/base.html`, so it can no
  longer collide with a host project's own `email_index.html`. The old
  `email_index.html` remains as a deprecated forwarding shim, so any custom
  template that still `{% extends "email_index.html" %}` keeps working.
- `LinkCounter.requester` now references `settings.AUTH_USER_MODEL` directly
  instead of a module-level `get_user_model()` call (migration-neutral).
- Added a common base exception, `verify_email.errors.VerifyEmailError`; every
  package exception now inherits from it, so integrators can catch the whole
  family with a single `except`.
- Declared `Django>=4.2` as an install dependency and verified compatibility with
  Django 4.2, 5.0, 5.1 and 5.2 on Python 3.8–3.12.

### Packaging / tooling
- Consolidated packaging metadata into `pyproject.toml` (PEP 621); removed
  `setup.cfg`/`setup.py`. Fixed the author email and stale/incorrect classifiers.
- Tests moved out of the installed package (into the repo-root `tests/` package),
  so the published wheel/sdist contain only `verify_email` — no test code.
- Added a `tox` matrix and a GitHub Actions test workflow across supported
  Python/Django versions (`tests.yml`).
- Releasing is now **manual and tag-based** via the `Release` workflow
  (`release.yml`): it builds with `python -m build`, validates with
  `twine check`, uploads to PyPI, tags `v<version>`, and creates a GitHub
  Release. (There is no publish-on-merge.)
