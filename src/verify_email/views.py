import logging

from django.forms import ValidationError
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.signing import SignatureExpired, BadSignature
from django.utils.translation import gettext as _

from .app_configurations import GetFieldFromSettings
from .confirm import verify_user
from .email_handler import resend_verification_email
from .forms import RequestNewVerificationEmail
from .errors import (
    InvalidToken,
    MaxRetriesExceeded,
    UserAlreadyActive,
    UserNotFound,
)

logger = logging.getLogger(__name__)

pkg_configs = GetFieldFromSettings()

login_page = pkg_configs.get('login_page')

success_msg = pkg_configs.get('verification_success_msg')
failed_msg = pkg_configs.get('verification_failed_msg')

failed_template = pkg_configs.get('verification_failed_template')
success_template = pkg_configs.get('verification_success_template')
link_expired_template = pkg_configs.get('link_expired_template')
request_new_email_template = pkg_configs.get('request_new_email_template')
new_email_sent_template = pkg_configs.get('new_email_sent_template')


def verify_user_and_activate(request, useremail, usertoken):
    """
    A view function already implemented for you so you don't have to implement any function for verification
    as this function will be automatically be called when user clicks on verification link.

    verify the user's email and token and redirect'em accordingly.
    """
    if request.method != 'GET':
        raise ValidationError(_('Method not allowed'))
    try:
        verified = verify_user(useremail, usertoken)
        if verified is True:
            if login_page and not success_template:
                messages.success(request, success_msg)
                return redirect(to=login_page)
            return render(
                request,
                template_name=success_template,
                context={
                    'msg': success_msg,
                    'status': _('Verification Successful!'),
                    'link': reverse(login_page)
                }
            )
        else:
            # we dont know what went wrong...
            raise ValueError
    except (ValueError, TypeError) as error:
        logger.error(f'[ERROR]: Something went wrong while verifying user, exception: {error}')
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': failed_msg,
                'minor_msg': _('There is something wrong with this link...'),
                'status': _('Verification Failed!'),
            }
        )
    except SignatureExpired:
        return render(
            request,
            template_name=link_expired_template,
            context={
                'msg': _('The link has lived its life :( Request a new one!'),
                'status': _('Expired!'),
                'encoded_email': useremail,
                'encoded_token': usertoken
            }
        )
    except BadSignature:
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _('This link was modified before verification.'),
                'minor_msg': _('Cannot request another verification link with faulty link.'),
                'status': _('Faulty Link Detected!'),
            }
        )
    except MaxRetriesExceeded:
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _('You have exceeded the maximum verification requests! Contact admin.'),
                'status': _('Maxed out!'),
            }
        )
    except InvalidToken:
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _('This link is invalid or been used already, we cannot verify using this link.'),
                'status': _('Invalid Link'),
            }
        )
    except UserNotFound:
        raise Http404(_("404 User not found"))


def request_new_link(request, useremail=None, usertoken=None):
    try:
        if useremail is None or usertoken is None:
            # request came from re-request email page
            if request.method == 'POST':
                form = RequestNewVerificationEmail(request.POST)  # do not inflate data
                if form.is_valid():
                    form_data: dict = form.cleaned_data
                    email = form_data['email']

                    inactive_user = get_user_model().objects.get(email=email)
                    if inactive_user.is_active:
                        raise UserAlreadyActive(_('User is already active'))
                    else:
                        # resend email
                        status = resend_verification_email(request, email, user=inactive_user, encoded=False)
                        if status:
                            return render(
                                request,
                                template_name=new_email_sent_template,
                                context={
                                    'msg': _("You have requested another verification email!"),
                                    'minor_msg': _('Your verification link has been sent'),
                                    'status': _('Email Sent!'),
                                }
                            )
                        else:
                            logger.error('something went wrong during sending email')
            else:
                form = RequestNewVerificationEmail()
            return render(
                request,
                template_name=request_new_email_template,
                context={'form': form}
            )
        else:
            # request came from  previously sent link
            status = resend_verification_email(request, useremail, token=usertoken)

        if status:
            return render(
                request,
                template_name=new_email_sent_template,
                context={
                    'msg': _("You have requested another verification email!"),
                    'minor_msg': _('Your verification link has been sent'),
                    'status': _('Email Sent!'),
                }
            )
        else:
            messages.info(request, _('Something went wrong during sending email :('))
            logger.error('something went wrong during sending email')

    except ObjectDoesNotExist as error:
        messages.warning(request, _('User not found associated with given email!'))
        logger.error(f'[ERROR]: User not found. exception: {error}')
        return HttpResponse(_(b"User Not Found"), status=404)

    except MultipleObjectsReturned as error:
        logger.error(f'[ERROR]: Multiple users found. exception: {error}')
        return HttpResponse(_(b"Internal server error!"), status=500)

    except KeyError as error:
        logger.error(f'[ERROR]: Key error for email in your form: {error}')
        return HttpResponse(_(b"Internal server error!"), status=500)

    except MaxRetriesExceeded as error:
        logger.error(f'[ERROR]: Maximum retries for link has been reached. exception: {error}')
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _('You have exceeded the maximum verification requests! Contact admin.'),
                'status': _('Maxed out!'),
            }
        )
    except InvalidToken:
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _('This link is invalid or been used already, we cannot verify using this link.'),
                'status': _('Invalid Link'),
            }
        )
    except UserAlreadyActive:
        return render(
            request,
            template_name=failed_template,
            context={
                'msg': _("This user's account is already active"),
                'status': _('Already Verified!'),
            }
        )
