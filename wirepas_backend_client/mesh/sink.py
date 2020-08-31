"""
    Sink
    ====

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_backend_client.mesh.device import MeshDevice


class Sink(MeshDevice):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    __name = "sink"

    # add allowed properties to filter out clutter

    def __init__(self, device_id: str, **kwargs):
        super(Sink, self).__init__(device_id=device_id, **kwargs)
        self.node_address = None
        self.app_config_data = None
        self.app_config_diag = None
        self.role = None
        self.firmware_version = None

    def set_app_config(self, **kwargs):
        """ placeholder for method handler """
