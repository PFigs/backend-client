"""
    MeshDevice
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_backend_client.tools.utils import JsonSerializer


class MeshDevice(object):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    # pylint: disable=locally-disabled, too-many-arguments, invalid-name

    __name = "node"

    def __init__(
        self,
        device_id: str,
        network_id: str = None,
        gateway_id: str = None,
        state: int = None,
        role: int = None,
    ):
        super(MeshDevice, self).__init__()
        self._device_id = str(device_id)
        self.__dict__["device_type"] = self.__name
        self.state = state
        self.role = role
        self.gateway_id = gateway_id
        self.network_id = network_id

    def update(self, configuration: dict):
        """ Takes a configuration dictionary and updates the
            internal properties
        """
        for k, v in configuration.items():
            if v is not None:
                self.__dict__[k] = v
                if "network_address" in k:
                    self.__dict__["network_id"] = v

    @property
    def device_id(self):
        """ returns the device identifier """
        return self._device_id

    def __str__(self):
        id_str = dict()
        for k, v in self.__dict__.items():

            if k == "_device_id":
                k = "device"

            if v is not None:
                id_str[k] = v
        try:
            obj = JsonSerializer(indent=None)
            id_str = obj.serialize(id_str)
        except TypeError:
            id_str = str(id_str)

        return id_str
