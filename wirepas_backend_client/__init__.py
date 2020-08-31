"""
    WIREPAS_BACKEND_CLIENT
    ======================

    A package to interface with Wirepas Backend Services, meant for
    testing, cloud to cloud integration and R&D.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
from wirepas_backend_client import api
from wirepas_backend_client import management
from wirepas_backend_client import messages
from wirepas_backend_client import tools

__all__ = ["api", "management", "messages", "tools"]
