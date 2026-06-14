from dataclasses import dataclass

from django.conf import settings

from .interface import DefaultConfig


@dataclass
class GetFieldFromSettings:
    """
    This class fetches the attributes that are defined in settings.py of your project by user OR Django itself.
    self.default_configs : is a dict with keys as the names used in this app and values being a tuple of
                           attributes defined in settings.py and their corresponding default values if not found.

    There is a special case in "get" method, if you set "VERIFICATION_SUCCESS_TEMPLATE" as None is settings.py, it
    will skip the intermediate page where success information is displayed. (This is better explained in docs.)

    The "get" method takes the name of the attributes as input, checks for it in settings.py,
            if found:
                returns the corresponding value.
            else:
                returns the default value from "self.defaults_configs".
    """

    def __post_init__(self):
        self.defaults_configs = {
            "debug": DefaultConfig(setting_field="DEBUG", default_value=False),
            "subject": DefaultConfig(
                setting_field="SUBJECT", default_value="Email Verification Mail"
            ),
            "email_field_name": DefaultConfig(
                setting_field="EMAIL_FIELD_NAME", default_value="email"
            ),
            "html_message_template": DefaultConfig(
                setting_field="HTML_MESSAGE_TEMPLATE",
                default_value="verify_email/email_verification_msg.html",
            ),
            "from_alias": DefaultConfig(
                setting_field="DEFAULT_FROM_EMAIL",
                default_value="<noreply<noreply@gmail.com>",
            ),
            "login_page": DefaultConfig(
                setting_field="LOGIN_URL", default_value="accounts_login"
            ),
            "verification_success_template": DefaultConfig(
                setting_field="VERIFICATION_SUCCESS_TEMPLATE",
                default_value="verify_email/email_verification_successful.html",
            ),
            "verification_success_msg": DefaultConfig(
                setting_field="VERIFICATION_SUCCESS_MSG",
                default_value=(
                    "Your Email is verified successfully and account has been activated."
                    " You can login with the credentials now..."
                ),
            ),
            "verification_failed_template": DefaultConfig(
                setting_field="VERIFICATION_FAILED_TEMPLATE",
                default_value="verify_email/email_verification_failed.html",
            ),
            "link_expired_template": DefaultConfig(
                setting_field="LINK_EXPIRED_TEMPLATE",
                default_value="verify_email/link_expired.html",
            ),
            "verification_failed_msg": DefaultConfig(
                setting_field="VERIFICATION_FAILED_MSG",
                default_value="There is something wrong with this link, can't verify the user...",
            ),
            "request_new_email_template": DefaultConfig(
                setting_field="REQUEST_NEW_EMAIL_TEMPLATE",
                default_value="verify_email/request_new_email.html",
            ),
            "new_email_sent_template": DefaultConfig(
                setting_field="NEW_EMAIL_SENT_TEMPLATE",
                default_value="verify_email/new_email_sent.html",
            ),
            "salt": DefaultConfig(setting_field="HASH_SALT", default_value=None),
            "sep": DefaultConfig(setting_field="SEPARATOR", default_value=":"),
            "key": DefaultConfig(setting_field="HASHING_KEY", default_value=None),
            "max_age": DefaultConfig(setting_field="EXPIRE_AFTER", default_value=None),
            "max_retries": DefaultConfig(setting_field="MAX_RETRIES", default_value=2),
        }

    def get(self, field_name, raise_exception=True):
        config = self.defaults_configs[field_name]
        attr = getattr(settings, config.setting_field, config.default_value)

        # Documented feature: setting VERIFICATION_SUCCESS_TEMPLATE = None
        # intentionally skips the success page and redirects to LOGIN_URL.
        if field_name == "verification_success_template" and attr is None:
            return None

        if attr is None and raise_exception:
            raise AttributeError(
                f"Set the '{config.setting_field}' value in your project's settings.py."
            )
        return attr
