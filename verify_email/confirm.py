import logging
from dataclasses import dataclass, field

from django.utils import timezone

from .custom_types import User
from .errors import UserAlreadyActive
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


@dataclass
class UserActivationProcess:
    """
    This class handles the process of activating a user account
    by verifying a token associated with the user's email.

    Attributes
    ----------
    token_manager : TokenManager
        An instance of TokenManager used to manage token operations.

    Methods
    -------
    activate_user(encoded_email: str, encoded_token: str) -> None:
        Activates the user account after verifying the provided token.

    Exceptions Raised
    ------------------
    - MaxRetriesExceeded: Raised when the maximum number of retries for verification is exceeded.
    - BadSignature: Raised when the token signature is invalid.
    - SignatureExpired: Raised when the token has expired.
    - ValueError: Raised for invalid values during verification.
    - TypeError: Raised for incorrect types during verification.
    - InvalidToken: Raised when the provided token is invalid.
    """

    token_manager: TokenManager = field(default_factory=TokenManager)

    @classmethod
    def activate_user(cls, encoded_email: str, encoded_token: str) -> User:
        """
        Steps to activate a user account:
        1. Verify the token.
        2. Set the user as active.
        3. Update the last login time.

        Parameters
        ----------
        encoded_email : str
            The encoded email address of the user.
        encoded_token : str
            The encoded token for user verification.

        Raises
        ------
        MaxRetriesExceeded
            If the maximum number of retries for token verification is exceeded.
        BadSignature
            If the token signature is invalid.
        SignatureExpired
            If the token has expired.
        ValueError
            If an invalid value is encountered during verification.
        TypeError
            If an incorrect type is provided.
        InvalidToken
            If the provided token is invalid.

        Notes
        -----
        This method instantiates the class to access its methods. This
        approach may be revised in the future as part of the class design
        considerations.
        """
        self = cls()  # Consider if instantiation is necessary here
        try:
            # Verify token and retrieve user object
            # this will return inactive user
            user = self.token_manager.decrypt_token_and_get_user(
                encoded_email, encoded_token
            )

            # Defense-in-depth: never re-activate an already-active account.
            # Normally the token check already fails for active users (it is
            # bound to last_login), but an account activated out-of-band could
            # still present a valid token; refuse rather than reset last_login.
            if user.is_active:
                raise UserAlreadyActive(
                    f"The user with email for token {encoded_email} is already active"
                )

            # Activate the user account
            user.is_active = True
            user.last_login = timezone.now()
            user.save()
            return user
        except Exception as err:
            logger.exception(err)
            # Perform any necessary cleanup if required
            raise
