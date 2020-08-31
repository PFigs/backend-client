"""
    Backend
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
# pylint: disable=locally-disabled, duplicate-code

from wirepas_backend_client.tools import Settings


class WNTSettings(Settings):
    """WNT Settings"""

    _MANDATORY_FIELDS = ["wnt_username", "wnt_password", "wnt_hostname"]

    def __init__(self, settings: Settings) -> "WNTSettings":

        self.wnt_username = None
        self.wnt_password = None
        self.wnt_hostname = None

        super(WNTSettings, self).__init__(settings)

    def __str__(self):
        return super()._helper_str(key_filter="wnt")
