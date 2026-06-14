import time

from django import forms
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

import verify_email
from verify_email.confirm import UserActivationProcess
from verify_email.email_handler import ActivationMailManager, send_verification_email
from verify_email.errors import InvalidToken, UserAlreadyActive, VerifyEmailError
from verify_email.token_manager import ActivationLinkManager, SafeURL, TokenManager

User = get_user_model()


class SignupForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]


class VerifyEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass",
        )
        self.user.is_active = False
        self.user.save()

    # --- Sending / verifying happy paths -------------------------------------

    def test_send_verification_email(self):
        """A verification email is sent for an inactive user."""
        response = ActivationMailManager.send_verification_link(self.user)
        self.assertIsNotNone(response)
        self.assertEqual(len(mail.outbox), 1)

    def test_public_api_send_verification_email(self):
        """
        The documented public entry point ``send_verification_email(request, form)``
        must exist, be importable from the package root, save the user as
        inactive, and send exactly one email.
        """
        self.assertIs(verify_email.send_verification_email, send_verification_email)

        request = RequestFactory().post("/signup/")
        form = SignupForm(data={"username": "fresh", "email": "fresh@example.com"})
        self.assertTrue(form.is_valid())

        inactive_user = send_verification_email(request, form)

        self.assertFalse(inactive_user.is_active)
        self.assertEqual(inactive_user.email, "fresh@example.com")
        self.assertEqual(len(mail.outbox), 1)

    def test_verification_view_by_token_and_email(self):
        user_token = TokenManager().generate_token_for_user(self.user)
        user_email = SafeURL.perform_encoding(self.user.email)
        response = self.client.get(
            reverse("verify-email", args=[user_email, user_token])
        )
        self.assertEqual(response.status_code, 200)

    def test_verification_link(self):
        user_token = TokenManager().generate_token_for_user(self.user)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)
        resp = self.client.get(f"http://testserver{link}")
        self.assertEqual(resp.status_code, 200)

    def test_activation_activates_user_and_sets_last_login(self):
        user_token = TokenManager().generate_token_for_user(self.user)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)
        self.client.get(f"http://testserver{link}")

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNotNone(self.user.last_login)

    def test_used_link_cannot_be_replayed(self):
        """Once a link activates the account, the same link no longer works."""
        user_token = TokenManager().generate_token_for_user(self.user)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)

        first = self.client.get(f"http://testserver{link}")
        self.assertEqual(first.status_code, 200)

        second = self.client.get(f"http://testserver{link}")
        self.assertEqual(second.status_code, 401)

    # --- Token expiry --------------------------------------------------------

    def test_process(self):
        user_token = TokenManager().generate_token_for_user(self.user)
        time.sleep(1)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)
        resp = self.client.get(f"http://testserver{link}")
        self.assertEqual(resp.status_code, 200)

    @override_settings(EXPIRE_AFTER="1s")
    def test_timestamp_invalid_link(self):
        """With EXPIRE_AFTER set, a stale link is rejected."""
        user_token = TokenManager().generate_token_for_user(self.user)
        time.sleep(3)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)
        resp = self.client.get(f"http://testserver{link}")
        self.assertEqual(resp.status_code, 401)

    def test_timestamp_valid_link(self):
        """Without EXPIRE_AFTER, the link stays valid (until used)."""
        user_token = TokenManager().generate_token_for_user(self.user)
        time.sleep(3)
        link = ActivationLinkManager.generate_link(user_token, self.user.email)
        resp = self.client.get(f"http://testserver{link}")
        self.assertEqual(resp.status_code, 200)

    # --- Token lookup with duplicate emails ----------------------------------

    def test_get_user_by_token_with_duplicate_emails(self):
        """
        Django's default user model does not enforce unique emails. The token
        must still resolve to the correct user even when another user shares the
        same address (regression test for the early-return loop bug).
        """
        other = User.objects.create_user(
            username="other", email=self.user.email, password="x"
        )
        other.is_active = False
        other.save()

        raw_token = TokenManager().generate_token_for_user(other, get_url_encoded=False)
        resolved = TokenManager.get_user_by_token(self.user.email, raw_token)
        self.assertEqual(resolved.pk, other.pk)

    def test_get_user_by_token_invalid(self):
        with self.assertRaises(InvalidToken):
            TokenManager.get_user_by_token(self.user.email, "not-a-real-token")
        # InvalidToken is part of the public error hierarchy.
        self.assertTrue(issubclass(InvalidToken, VerifyEmailError))

    def test_already_active_account_is_not_reactivated(self):
        """
        An already-active account presenting a still-valid token must be refused
        (defense-in-depth), not silently re-activated.
        """
        # Active user whose token still validates because last_login is None.
        active = User.objects.create_user(
            username="already", email="already@example.com", password="x"
        )
        active.is_active = True
        active.last_login = None
        active.save()

        token = TokenManager().generate_token_for_user(active)
        email = SafeURL.perform_encoding(active.email)

        with self.assertRaises(UserAlreadyActive):
            UserActivationProcess.activate_user(email, token)

        active.refresh_from_db()
        self.assertIsNone(active.last_login)  # untouched


class RequestNewLinkEnumerationTests(TestCase):
    """The public resend form must not reveal whether an email is registered."""

    def setUp(self):
        self.url = reverse("request-new-link-from-email")
        self.pending = User.objects.create_user(
            username="pending", email="pending@example.com", password="x"
        )
        self.pending.is_active = False
        self.pending.save()

        self.active = User.objects.create_user(
            username="active", email="active@example.com", password="x"
        )

    def _post(self, email):
        return self.client.post(self.url, data={"email": email})

    def test_pending_user_gets_email(self):
        resp = self._post("pending@example.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_same_response_no_mail(self):
        resp = self._post("nobody@example.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_active_user_same_response_no_mail(self):
        resp = self._post("active@example.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_responses_are_indistinguishable(self):
        """Body for unknown vs. active vs. pending must be identical."""
        bodies = {
            self._post(email).content
            for email in ("pending@example.com", "active@example.com", "x@example.com")
        }
        self.assertEqual(len(bodies), 1)


class LinkCounterTests(TestCase):
    """The LinkCounter is created lazily (no global signal) and caps resends."""

    def setUp(self):
        self.url = reverse("request-new-link-from-email")
        self.user = User.objects.create_user(
            username="pending", email="pending@example.com", password="x"
        )
        self.user.is_active = False
        self.user.save()

    def test_no_counter_created_at_signup(self):
        """Creating a user must NOT create a LinkCounter (signal removed)."""
        from verify_email.models import LinkCounter

        self.assertFalse(LinkCounter.objects.filter(requester=self.user).exists())

    def test_counter_created_lazily_on_first_resend(self):
        from verify_email.models import LinkCounter

        self._resend()
        counter = LinkCounter.objects.get(requester=self.user)
        # sent_count starts at 1 (initial email) and is incremented once.
        self.assertEqual(counter.sent_count, 2)

    @override_settings(MAX_RETRIES=2)
    def test_resend_limit_is_enforced(self):
        # cap = MAX_RETRIES + 1 = 3; counter starts at 1 -> 2 resends allowed.
        self.assertEqual(self._resend().status_code, 200)
        self.assertEqual(self._resend().status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

        # Third resend is over the limit: still a generic 200, but no new email.
        self.assertEqual(self._resend().status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def _resend(self):
        return self.client.post(self.url, data={"email": self.user.email})


class TemplateTests(TestCase):
    """Templates use a namespaced base; the old name stays as a compat shim."""

    def test_request_new_email_form_page_renders(self):
        resp = self.client.get(reverse("request-new-link-from-email"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<form")

    def test_deprecated_email_index_shim_still_extends(self):
        """
        A custom template that still `{% extends "email_index.html" %}` (the old,
        un-namespaced base) must keep rendering via the shim -> verify_email/base.html.
        """
        from django.template import engines

        template = engines["django"].from_string(
            '{% extends "email_index.html" %}{% block content %}SHIM_OK{% endblock %}'
        )
        self.assertIn("SHIM_OK", template.render({"status": "x"}))
