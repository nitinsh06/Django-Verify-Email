"""Exceptions raised by verify_email.

All exceptions inherit from :class:`VerifyEmailError`, so integrators can catch
the whole family with a single ``except VerifyEmailError`` if they prefer.
"""


class VerifyEmailError(Exception):
    """Base class for every error raised by this package."""


class UserAlreadyActive(VerifyEmailError):
    pass


class MaxRetriesExceeded(VerifyEmailError):
    pass


class UserNotFound(VerifyEmailError):
    pass


class InvalidToken(VerifyEmailError):
    pass


class InvalidTokenOrEmail(VerifyEmailError):
    pass


class WrongTimeInterval(VerifyEmailError):
    pass


class DecodingFailed(VerifyEmailError):
    pass


__all__ = [
    "VerifyEmailError",
    "UserAlreadyActive",
    "MaxRetriesExceeded",
    "UserNotFound",
    "InvalidToken",
    "InvalidTokenOrEmail",
    "WrongTimeInterval",
    "DecodingFailed",
]
