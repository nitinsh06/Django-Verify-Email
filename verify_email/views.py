import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from .app_configurations import GetFieldFromSettings
from .confirm import UserActivationProcess
from .email_handler import ActivationMailManager
from .errors import (
    InvalidToken,
    MaxRetriesExceeded,
    UserAlreadyActive,
    UserNotFound,
)
from .forms import RequestNewVerificationEmail

logger = logging.getLogger(__name__)

pkg_configs = GetFieldFromSettings()

login_page = pkg_configs.get("login_page")

success_msg = pkg_configs.get("verification_success_msg")
failed_msg = pkg_configs.get("verification_failed_msg")
debug = pkg_configs.get("debug")

failed_template = pkg_configs.get("verification_failed_template")
success_template = pkg_configs.get("verification_success_template")
link_expired_template = pkg_configs.get("link_expired_template")
request_new_email_template = pkg_configs.get("request_new_email_template")
new_email_sent_template = pkg_configs.get("new_email_sent_template")


@require_GET
def verify_and_activate_user(request, user_email, user_token):
    """
    A view function already implemented for you so you don't have to implement any function for verification
    as this function will be automatically be called when user clicks on verification link.

    verify the user's email and token and redirect'em accordingly.
    """
    try:
        UserActivationProcess.activate_user(user_email, user_token)
        if login_page and not success_template:
            messages.success(request, success_msg)
            return redirect(to=login_page)

        return render(
            request,
            template_name=success_template,
            context={
                "msg": success_msg,
                "status": "Verification Successful!",
                "link": reverse(login_page),
            },
        )

    except (ValueError, TypeError) as error:
        logger.error(
            f"[ERROR]: Something went wrong while verifying user, exception: {error}"
        )
        return render(
            request,
            status=401,
            template_name=failed_template,
            context={
                "msg": failed_msg,
                "minor_msg": "There is something wrong with this link...",
                "status": "Verification Failed!",
            },
        )
    except SignatureExpired:
        return render(
            request,
            status=401,
            template_name=link_expired_template,
            context={
                "msg": "The link has lived its life :( Request a new one!",
                "status": "Expired!",
                "encoded_email": user_email,
                "encoded_token": user_token,
            },
        )
    except BadSignature:
        return render(
            request,
            status=401,
            template_name=failed_template,
            context={
                "msg": "This link was modified before verification.",
                "minor_msg": "Cannot request another verification link with faulty link.",
                "status": "Faulty Link Detected!",
            },
        )
    except MaxRetriesExceeded:
        return render(
            request,
            status=401,
            template_name=failed_template,
            context={
                "msg": "You have exceeded the maximum verification requests! Contact admin.",
                "status": "Maxed out!",
            },
        )
    except InvalidToken:
        return render(
            request,
            status=401,
            template_name=failed_template,
            context={
                "msg": "This link is invalid or been used already, we cannot verify using this link.",
                "status": "Invalid Link",
            },
        )
    except UserNotFound:
        raise Http404("404 User not found")

    except UserAlreadyActive:
        return render(
            request,
            template_name=failed_template,
            context={
                "msg": "This account is already verified. You can log in.",
                "status": "Already Verified!",
            },
        )

    except Exception as err:
        logger.exception(err)
        flash_msg = "Something went wrong during this process!"
        if debug:
            flash_msg = f"""{flash_msg} Developer should look into this.
            Error Details: {err}
            (You are seeing error details because app is running in debug mode)
            """
        return render(
            request,
            status=403,
            template_name=failed_template,
            context={
                "msg": flash_msg,
                "status": "Failed!",
            },
        )



def _email_sent_response(request):
    """
    Enumeration-safe confirmation page.

    Rendered identically whether or not the email belongs to a real account
    and regardless of that account's state, so this endpoint cannot be used to
    probe which addresses are registered or already verified.
    """
    return render(
        request,
        template_name=new_email_sent_template,
        context={
            "msg": "If an account with that email exists and still needs "
            "verification, a new link has been sent.",
            "minor_msg": "Check your inbox (and your spam folder).",
            "status": "Email Sent!",
        },
    )


def _failed_response(request, msg, status_label, http_status=403):
    flash_msg = msg
    if debug:
        flash_msg = (
            f"{msg} (You are seeing extra details because the project runs in DEBUG mode.)"
        )
    return render(
        request,
        status=http_status,
        template_name=failed_template,
        context={"msg": flash_msg, "status": status_label},
    )


@require_http_methods(["GET", "POST"])
def request_new_link(request, user_email=None, user_token=None):
    """
    Re-issue a verification link.

    Two entry points share this view:
      * The public "request a new email" form (no token in the URL). The
        response here is deliberately uniform to avoid account enumeration.
      * The "request new link" button on an expired-link page (email + token in
        the URL). The caller already holds a token, so specific feedback is safe.
    """
    # --- Path 1: public form, no token. Must not leak account existence. ---
    if user_email is None or user_token is None:
        if request.method == "POST":
            form = RequestNewVerificationEmail(request.POST)
            if form.is_valid():
                email = form.cleaned_data["email"]
                try:
                    inactive_user = get_user_model().objects.get(email=email)
                    if not inactive_user.is_active:
                        ActivationMailManager.resend_verification_link(
                            request, email, user=inactive_user, encoded=False
                        )
                except (
                    ObjectDoesNotExist,
                    MultipleObjectsReturned,
                    UserAlreadyActive,
                    MaxRetriesExceeded,
                ) as error:
                    # Swallow: revealing any of these would enable enumeration.
                    logger.info("Resend request not fulfilled silently: %s", error)
                except Exception as err:  # noqa: BLE001 - log but stay generic
                    logger.exception(err)
                return _email_sent_response(request)
        else:
            form = RequestNewVerificationEmail()
        return render(
            request,
            template_name=request_new_email_template,
            context={"form": form},
        )

    # --- Path 2: from an expired link (email + token present in the URL). ---
    try:
        ActivationMailManager.resend_verification_link(
            request, user_email, token=user_token
        )
        return _email_sent_response(request)
    except MaxRetriesExceeded as error:
        logger.error("Maximum retries for link reached: %s", error)
        return _failed_response(
            request,
            "You have exceeded the maximum verification requests! Contact admin.",
            "Maxed out!",
        )
    except UserAlreadyActive:
        return _failed_response(
            request, "This account is already active.", "Already Verified!"
        )
    except (InvalidToken, UserNotFound):
        return _failed_response(
            request,
            "This link is invalid or has already been used; we cannot verify it.",
            "Invalid Link",
        )
    except Exception as err:
        logger.exception(err)
        return _failed_response(
            request, "Something went wrong during this process!", "Failed!"
        )
