# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`Django-Verify-Email` is a reusable Django **app** (not a standalone project) published to PyPI as `Django-Verify-Email`. It handles two-step email verification for new signups: it sets a new user to `is_active=False`, emails them a signed verification link, and activates the account when the link is visited. Version lives in `setup.cfg` (`version = ...`); the current major is 3.x.

The package is installed into a host project that supplies `settings.py`, the user model, and a mail backend. A minimal test harness lives under `tests/` (see [Tests](#tests)).

## Public API

The intended public entry point is re-exported from the package root (`verify_email/__init__.py` → `email_handler`):

- `send_verification_email(request, form)` — the documented signup helper. It is a thin wrapper around `ActivationMailManager.send_verification_link(form=..., request=...)`. Saves the form's user as inactive and emails the link; returns the inactive user (with `.cleaned_data`). If sending fails, the user is **deleted** so signup can be retried. (This wrapper was missing in 3.0.x — the documented import raised `ImportError` — and was restored in 3.1.0; keep it and its regression test, `test_public_api_send_verification_email`.)

Verification and "resend link" flows are fully handled by the app's own views/URLs — host projects only `include('verify_email.urls')`; they do not write verification views.

## Architecture

The flow is layered; each layer has a single responsibility:

- **`email_handler.py` — `ActivationMailManager`** (frozen dataclass): orchestration layer. `send_verification_link` (inactivate + save user, build URL, render template, send) and `resend_verification_link` (decode prior link or look up by email, re-issue). Composes a `TokenManager` and `GetFieldFromSettings`.
- **`token_manager.py`** — all crypto/signing logic. `TokenManager` subclasses `django.core.signing.TimestampSigner` **and** `GeneralConfig` (multiple inheritance; `__post_init__` must call `GeneralConfig.__post_init__` then `TimestampSigner.__init__`). Key pieces:
  - `SafeURL` — urlsafe base64 encode/decode of email and token for the URL.
  - `ActivationLinkManager` — builds the link via `reverse('verify-email', ...)` (so the mount prefix is not hard-coded), and enforces resend limits via `can_request_new_link` / sent-count.
  - Token = Django's `default_token_generator` token, optionally wrapped by the timestamp signer **only when `EXPIRE_AFTER` (`max_age`) is set**. This is the central branch: with no `max_age` the link "expires after one use"; with `max_age` set it expires by time and `SignatureExpired` triggers the resend path. `decrypt_token_and_get_user` is the verification workhorse and distinguishes `SignatureExpired` (offer new link) from `BadSignature` (tampered — refuse).
- **`confirm.py` — `UserActivationProcess.activate_user`** — verifies token via `TokenManager`, sets `is_active=True` and `last_login=now()`.
- **`views.py`** — `verify_and_activate_user` (GET only) and `request_new_link`. These map the many domain exceptions (`InvalidToken`, `MaxRetriesExceeded`, `UserAlreadyActive`, `UserNotFound`, `SignatureExpired`, `BadSignature`) to specific templates/HTTP statuses. This exception-to-template mapping is the bulk of view logic — preserve it when editing.
- **`app_configurations.py` — `GetFieldFromSettings`** — the single source of truth for every setting the app reads. All settings have defaults and are accessed through `.get("<key>")`. **Add any new configurable setting here**, not via direct `settings.` access elsewhere. Special case: `VERIFICATION_SUCCESS_TEMPLATE = None` skips the success page and redirects to `LOGIN_URL`.
- **`models.py` — `LinkCounter`** — one-to-one with the user (`settings.AUTH_USER_MODEL`), tracks `sent_count` for resend-limit enforcement (`MAX_RETRIES`). The counter is created **lazily** by `ActivationLinkManager._get_or_create_counter` on the first resend (`sent_count` starts at 1). There is no `signals.py` and no global `post_save` handler — earlier versions created a counter for every user in the project; that was removed. Existing rows are reused untouched, so no migration is needed.
- **`errors.py`** — domain exceptions raised by lower layers and caught in `views.py`.
- **`custom_types.py`** — `User` type alias.

URL structure (`urls.py`): verification link is `user/verify-email/<encoded_email>/<token>/`; resend has both a from-link form and a from-email form variant.

## Settings consumed

Read `GetFieldFromSettings.defaults_configs` for the authoritative list. Key ones: `EXPIRE_AFTER` (link lifetime; int = seconds, or suffix `s`/`m`/`h`/`d` — note `m` is minutes), `MAX_RETRIES`, `EMAIL_FIELD_NAME`, `HTML_MESSAGE_TEMPLATE`, `HASHING_KEY`/`HASH_SALT`/`SEPARATOR` (signer config), `SUBJECT`, and the `*_TEMPLATE` / `*_MSG` overrides. Host project must also configure a Django mail backend and `DEFAULT_FROM_EMAIL`.

## Tests

`verify_email/tests.py` uses `django.test.TestCase` and exercises the real send/verify flow against the configured user model and mail outbox. The repo ships a minimal harness in `tests/` (`tests/settings.py`, `tests/urls.py`). Run them with either:

```
DJANGO_SETTINGS_MODULE=tests.settings pytest verify_email
DJANGO_SETTINGS_MODULE=tests.settings python -m django test verify_email
tox            # full Python x Django matrix
```

`tests/urls.py` mounts `verify_email.urls` at `verification/` and defines a `login` URL (needed because the success view reverses `LOGIN_URL`). Several tests use `time.sleep` to assert expiry behaviour, so the suite is intentionally slow. The `tests/` package is excluded from the built wheel/sdist.

## Build & release

Packaging metadata lives entirely in `pyproject.toml` (PEP 621; there is no longer a `setup.py`/`setup.cfg`). `Django>=4.2` is a declared dependency. Build with `python -m build`; validate with `twine check dist/*`. Releases publish to PyPI via `.github/workflows/python-publish.yml` (on push to `main`, on a published GitHub release, or manual dispatch). `.github/workflows/tests.yml` runs the test matrix on push/PR. Bump `version` in `pyproject.toml` for a release and add a `CHANGELOG.md` entry.

## Conventions

- Most core classes are `@dataclass`es that compose their collaborators via `field(default_factory=...)`. Follow this pattern rather than instantiating dependencies inline.
- All settings access goes through `GetFieldFromSettings`; lower layers raise typed exceptions from `errors.py` and let `views.py` decide the user-facing response.
