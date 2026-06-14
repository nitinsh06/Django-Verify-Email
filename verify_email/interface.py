from dataclasses import dataclass
from typing import Any, Union


@dataclass
class DefaultConfig:
    """Default configuration for the application."""

    setting_field: str
    default_value: Union[str, Any]
