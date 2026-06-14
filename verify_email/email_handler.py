import logging
from dataclasses import dataclass, field

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .app_configurations import GetFieldFromSettings
from .custom_types import User
from .errors import InvalidTokenOrEmail
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

__all__ = ["ActivationMailManager", "send_verification_email"]


@dataclass(frozen=True)
class ActivationMailManager:
    """
    This class does two things:
    1. set each user as inactive and saves it
    2. sends the email to user with that link.
    """

    token_manager: TokenManager = field(default_factory=TokenManager)
    settings: GetFieldFromSettings = field(default_factory=GetFieldFromSettings)

    def _generate_verification_url(
        self, inactive_user: User, user_email: str, request=None
    ):
        token = self.token_manager.generate_token_for_user(inactive_user)
        link = (
            self.token_manager.link_manager.generate_link(token, user_email)
            if not request
            else self.token_manager.link_manager.get_absolute_verification_url(
                request, token, user_email
            )
        )
        return link

    # Private :
    def _send_email(self, msg, useremail):
        subject = self.settings.get("subject")
        send_mail(
            subject,
            strip_tags(msg),
            from_email=self.settings.get("from_alias"),
            recipient_list=[useremail],
            html_message=msg,
        )

    # Public :
    @classmethod
    def send_verification_link(cls, inactive_user=None, form=None, request=None):
        self = cls()

        if form:
            inactive_user = form.save(commit=False)

        inactive_user.is_active = False
        inactive_user.save()

        try:

            useremail = (
                form.cleaned_data.get(self.settings.get("email_field_name"))
                if form
                else inactive_user.email
            )
            if not useremail:
                raise KeyError(
                    'No key named "email" in your form. Your field should be named as email in form OR set a variable'
                    ' "EMAIL_FIELD_NAME" with the name of current field in settings.py if you want to use current name '
                    "as email field."
                )

            verification_url = self._generate_verification_url(
                inactive_user, useremail, request=request
            )
            msg = render_to_string(
                self.settings.get("html_message_template", raise_exception=True),
                {"link": verification_url, "inactive_user": inactive_user},
                request=request,
            )

            self._send_email(msg, useremail)
            return inactive_user
        except Exception:
            inactive_user.delete()
            raise

    @classmethod
    def resend_verification_link(cls, request, email, **kwargs):
        """
        This method needs the previously sent link to get encoded email and token from that.
        Exceptions Raised
        -----------------
            - UserAlreadyActive (by) get_user_by_token()
            - MaxRetryExceeded  (by) request_new_link()
            - InvalidTokenOrEmail

        These exception should be handled in caller function.
        """
        self = cls()

        try:
            inactive_user = kwargs.get("user")
            user_encoded_token = kwargs.get("token")
            encoded = kwargs.get("encoded", True)

            if not inactive_user or not email:
                raise InvalidTokenOrEmail(
                    f"Either token or email is invalid. user: {inactive_user}, email: {email}"
                )

            if encoded:
                decoded_enc_user_token = (
                    self.token_manager.safe_url_encoder.perform_decoding(
                        user_encoded_token
                    )
                )
                decoded_email = self.token_manager.safe_url_encoder.perform_decoding(
                    email
                )
                inactive_user = self.token_manager.get_user_by_token(
                    decoded_email, decoded_enc_user_token
                )

            # At this point, we have decoded email(if it was encoded), and inactive_user, and we can request new link
            new_token = self.token_manager.generate_token_for_user(inactive_user)
            link = self.token_manager.link_manager.request_new_link(
                request, inactive_user, new_token, email
            )
            msg = render_to_string(
                self.settings.get("html_message_template", raise_exception=True),
                {"link": link},
                request=request,
            )
            self._send_email(msg, email)
            return True
        except Exception as err:
            logger.error(
                f"Error occurred during re sending the email with verification link: {err}"
            )
            raise err


def send_verification_email(request, form):
    """
    Primary entry point: save ``form``'s user as inactive and email them a
    verification link.

    This is the documented public API used from a signup view. It is a thin
    wrapper around :meth:`ActivationMailManager.send_verification_link` and
    returns the saved (inactive) user, so you do not need to call ``form.save()``
    yourself. If sending fails the user is rolled back so the visitor can retry.
    """
    return ActivationMailManager.send_verification_link(form=form, request=request)
