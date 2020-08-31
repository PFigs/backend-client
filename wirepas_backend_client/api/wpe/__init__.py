"""

    WPE
    ===

    This module contains classes to allow the interaction with
    WPE public API (grpc)

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

# flake8: noqa

from .__main__ import main as wpe_main
from .connectors import Service
from .settings import WPESettings

__all__ = ["Service", "WPESettings", "wpe_main"]
