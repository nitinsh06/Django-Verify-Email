# Django-Verify-Email

[![PyPI version](https://img.shields.io/pypi/v/Django-Verify-Email.svg)](https://pypi.org/project/Django-Verify-Email/)
[![Python versions](https://img.shields.io/pypi/pyversions/Django-Verify-Email.svg)](https://pypi.org/project/Django-Verify-Email/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Drop-in **two-step email verification** for Django sign-ups. On registration the
app deactivates the new account, emails the user a signed, single-use
verification link, and re-activates the account when that link is opened — all
without you writing any verification views.

- **Compatible with** Django 4.2, 5.0, 5.1, 5.2 on Python 3.8–3.12.
- Works with any `AUTH_USER_MODEL` (uses `get_user_model()`).
- Signed, expiring links built on Django's own token machinery.
- Built-in "resend verification email" flow (by form or from an expired link).
- Every page and email is template-overridable.

> **Upgrading?** See [`CHANGELOG.md`](CHANGELOG.md). `3.1.0` is a
> backwards-compatible release; public imports, URL names, template paths and
> settings are unchanged.

---

## How it works

1. You call `send_verification_email(request, form)` from your signup view.
2. The app saves the user with `is_active = False` and emails a verification link.
3. The user clicks the link; the app validates the signed token, sets
   `is_active = True` and `last_login = now()`, and shows a success page (or
   redirects straight to login).
4. Used, tampered, or expired links are rejected and routed to the appropriate
   page; expired links can offer the user a new one.

You do **not** write any verification view — the app ships its own URLs and views.

---

## Installation

```bash
pip install Django-Verify-Email
```

### 1. Configure email (skip if your project already sends mail)

```python
# settings.py
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ["EMAIL_ID"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_PW"]

DEFAULT_FROM_EMAIL = "noreply <no_reply@domain.com>"
```

### 2. Add the app

```python
INSTALLED_APPS = [
    # ...
    "verify_email.apps.VerifyEmailConfig",
]
```

### 3. Include the URLs

```python
# project/urls.py
urlpatterns = [
    # ...
    path("verification/", include("verify_email.urls")),
]
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Send the verification email from your signup view

```python
from verify_email.email_handler import send_verification_email

def register_user(request):
    form = MySignupForm(request.POST)
    if form.is_valid():
        inactive_user = send_verification_email(request, form)
        # `inactive_user` is the saved user (is_active=False).
        # Access submitted data via inactive_user.cleaned_data['email'], etc.
        ...
```

`send_verification_email(request, form)` saves the user as inactive and sends the
link — you don't call `form.save()` yourself. **If sending the email fails, the
user is rolled back (deleted)** so the visitor can retry.

> Your form must have an `email` field. If it's named differently, set
> [`EMAIL_FIELD_NAME`](#configuration).

That's it — verification is fully handled by the app from here.

---

## Configuration

All settings are optional and read from your project's `settings.py`.

| Setting | Default | Purpose |
| --- | --- | --- |
| `SUBJECT` | `"Email Verification Mail"` | Subject line of the verification email. |
| `EMAIL_FIELD_NAME` | `"email"` | Name of the email field on your signup form. |
| `HTML_MESSAGE_TEMPLATE` | `verify_email/email_verification_msg.html` | Template for the email body. Must render `{{ link }}`. |
| `DEFAULT_FROM_EMAIL` | Django's default | From address for the email. |
| `LOGIN_URL` | `"accounts_login"` | URL name the success page links to. Also used by Django. |
| `VERIFICATION_SUCCESS_TEMPLATE` | `verify_email/email_verification_successful.html` | Success page. Set to `None` to skip it and redirect straight to `LOGIN_URL`. |
| `VERIFICATION_SUCCESS_MSG` | *(sensible default)* | Message shown on success. |
| `VERIFICATION_FAILED_TEMPLATE` | `verify_email/email_verification_failed.html` | Page shown for invalid/failed links. |
| `LINK_EXPIRED_TEMPLATE` | `verify_email/link_expired.html` | Page shown when a link has expired. |
| `VERIFICATION_FAILED_MSG` | *(sensible default)* | Message shown on failure. |
| `REQUEST_NEW_EMAIL_TEMPLATE` | `verify_email/request_new_email.html` | Page hosting the "request a new link" form. |
| `NEW_EMAIL_SENT_TEMPLATE` | `verify_email/new_email_sent.html` | Confirmation page after a new link is requested. |
| `EXPIRE_AFTER` | `None` | Link lifetime. See [Link expiry](#link-expiry). |
| `MAX_RETRIES` | `2` | How many times a user may request a new link. |
| `HASHING_KEY` | project `SECRET_KEY` | Key used to sign links. |
| `HASH_SALT` | `None` | Optional salt for the signer. |
| `SEPARATOR` | `":"` | Separator used by the signer. Must not be in the URL-safe base64 alphabet. |

---

## Link expiry

By default a link stays valid until it is used (subject to Django's
`PASSWORD_RESET_TIMEOUT`, which the underlying token honours — 3 days by
default). To set an explicit expiry, define `EXPIRE_AFTER`:

```python
EXPIRE_AFTER = "1d"   # 1 day
EXPIRE_AFTER = "2h"   # 2 hours
EXPIRE_AFTER = "30m"  # 30 minutes  (m = minutes, not months)
EXPIRE_AFTER = 90     # bare integer = seconds
```

Supported suffixes: `s` (seconds), `m` (minutes), `h` (hours), `d` (days). A
bare integer is treated as seconds.

---

## Resending verification emails

A user may request a new link up to `MAX_RETRIES` times (default `2`). After
that they are shown a "maxed out" page.

**From an expired link.** The expired-link page includes a button to request a
new email — no extra setup needed.

**From a form.** Link users to the request form via its URL name:

```html
<a href="{% url 'request-new-link-from-email' %}">Resend verification email</a>
```

This serves a form with a single `email` field. To customise it, point
`REQUEST_NEW_EMAIL_TEMPLATE` at your own template (the view passes a `form` in the
context):

```html
<form method="POST">
  {% csrf_token %}
  <fieldset>{{ form }}</fieldset>
  <button type="submit">Request New Email</button>
</form>
```

> The resend form is **enumeration-safe**: it returns the same response whether
> or not the address is registered, and whether or not the account is already
> active. It will not reveal which emails exist. (See
> [Security](#security-notes).)

> This feature stores per-user counters in the database, so make sure you've run
> migrations (step 4).

---

## Customising templates

Override any page or the email body by pointing the relevant setting at your own
template (see the [Configuration](#configuration) table).

**Email body** (`HTML_MESSAGE_TEMPLATE`) — context: `{{ request }}`, `{{ link }}`.
You **must** include `{{ link }}` or the email won't contain a working link:

```html
<a href="{{ link }}">Verify your email</a>
```

**Success page** (`VERIFICATION_SUCCESS_TEMPLATE`) — context: `{{ msg }}`,
`{{ link }}` (login URL), `{{ status }}`:

```html
<h1>{{ msg }}</h1>
<a href="{{ link }}">Login</a>
```

**Failed / expired pages** — context includes `{{ msg }}` and `{{ status }}`.

### Redirecting to login after success

- **Show a success page** that links to login: set `LOGIN_URL` to your login URL
  name.
- **Skip the success page** and go straight to login: set
  `VERIFICATION_SUCCESS_TEMPLATE = None`.

---

## Security notes

- Links are signed with Django's `TimestampSigner` using your `SECRET_KEY` (or a
  custom `HASHING_KEY`). Tampered links produce a `BadSignature` and are rejected
  outright — a modified link cannot be used to request a fresh one.
- The verification token is Django's `default_token_generator` token, bound to
  the user's password hash and `last_login`. Activating the account updates
  `last_login`, which **invalidates the link**, making links effectively
  single-use even without `EXPIRE_AFTER`.
- The "request a new email" form is enumeration-safe (identical response for
  unknown / pending / already-active accounts).
- Already-active accounts are never re-activated, even if a still-valid token is
  presented.
- Internal error details are only shown to end users when the project runs with
  `DEBUG = True`.

### Operational hardening (recommended)

- **Bound the resend window with `PASSWORD_RESET_TIMEOUT`.** By design, the
  "request a new link" button on an *expired*-link page accepts the expired
  token to mint a fresh link (that's the feature). The window in which an old
  link can still be exchanged for a new one is therefore governed by Django's
  `PASSWORD_RESET_TIMEOUT` (default **3 days**), independently of `EXPIRE_AFTER`,
  and is capped per user by `MAX_RETRIES`. If you set a short `EXPIRE_AFTER`,
  also lower `PASSWORD_RESET_TIMEOUT` to match your intended link lifetime.
- **Add request throttling.** The package caps resends per user (`MAX_RETRIES`)
  but does not rate-limit by IP, and the resend form is not constant-time (it
  sends an email only for valid pending accounts, a subtle timing signal). For
  internet-facing signups, put a throttle (e.g. `django-ratelimit`) in front of
  the resend endpoints and consider sending email asynchronously.

---

## Public API

```python
from verify_email.email_handler import send_verification_email  # primary entry point
from verify_email.errors import VerifyEmailError                # base of all package exceptions
```

URL names you can `reverse`/link to: `verify-email`,
`request-new-link-from-token`, `request-new-link-from-email`.

---

## Development

```bash
# install dev dependencies
pip install -e ".[dev]"

# run the test suite (config + settings come from pyproject.toml / tests/)
pytest

# or across all supported Python/Django versions
tox
```

---

## Contributing

Issues and pull requests are welcome at
<https://github.com/foo290/Django-Verify-Email>. There is always room for
improvement — feel free to open an issue or PR.

## License

Released under the [MIT License](LICENSE).
