"""Shared Monkey365 runner enums used across service, executor, and tests."""

from enum import Enum


class M365Provider(str, Enum):
    """Supported Monkey365 provider instances."""

    MICROSOFT365 = "Microsoft365"
