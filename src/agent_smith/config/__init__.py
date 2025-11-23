"""Configuration management for Agent Smith."""

from .paths import AppPaths
from .settings import get_api_key, set_api_key, settings

__all__ = ["settings", "get_api_key", "set_api_key", "AppPaths"]
