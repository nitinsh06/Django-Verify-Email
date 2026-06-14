from django.conf import settings
from django.db import models


class LinkCounter(models.Model):
    """
    Tracks how many verification links have been sent to a user, so the resend
    limit (``MAX_RETRIES``) can be enforced.

    A row is created lazily the first time a user requests a resend (see
    ``ActivationLinkManager``); there is no longer a global ``post_save`` signal
    creating one for every user in the project.
    """

    requester = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    sent_count = models.IntegerField()

    def __str__(self) -> str:
        return str(self.requester.get_username())

    def __repr__(self) -> str:
        return str(self.requester.get_username())
