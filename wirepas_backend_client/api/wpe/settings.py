"""
    Caller
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
# pylint: disable=locally-disabled, duplicate-code

from wirepas_backend_client.tools import Settings
from pathlib import Path


class WPESettings(Settings):
    """WPE Settings"""

    _MANDATORY_FIELDS = ["wpe_service_definition"]

    def __init__(self, settings: Settings) -> "WPESettings":

        self.wpe_service_definition = None
        self.wpe_network = None
        self.wpe_unsecure = False

        super(WPESettings, self).__init__(settings)

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = super().sanity()

        if self.wpe_service_definition is not None:
            definition_file = Path(self.wpe_service_definition)
            is_valid = definition_file.exists()

        return is_valid

    def __str__(self):
        return super()._helper_str(key_filter="wpe")
