"""Shared type aliases for the verify_email package."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Only imported for static type checking. Importing a Django model at
    # runtime here would touch the app registry before it is ready.
    from django.contrib.auth.models import AbstractBaseUser as User
else:
    User = Any

__all__ = ["User"]
