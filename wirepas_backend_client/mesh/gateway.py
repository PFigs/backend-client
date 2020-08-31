"""
    Gateway
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_backend_client.mesh.device import MeshDevice
from wirepas_backend_client.mesh.sink import Sink


class Gateway(MeshDevice):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    # pylint: disable=locally-disabled, too-many-arguments

    __name = "gateway"

    def __init__(self, device_id, network_id=None, **kwargs):
        super(Gateway, self).__init__(
            device_id=device_id, network_id=network_id, **kwargs
        )
        self.gateway_id = device_id
        self.state = None
        self._sinks = dict()
        self._nodes = dict()

    def add(self, devices: list(), device_type):
        """ Adds a mesh device to the gateway """
        attribute = None
        if "sink" in device_type:
            attribute = self._sinks

        if "node" in device_type:
            attribute = self._nodes

        if devices and attribute:
            for device in devices:
                if device.device_id not in attribute:
                    attribute[device.device_id] = device

    def remove(self, device_id):
        """ Removes a devices from the internal sink and node dictionary """
        if device_id in self._sinks:
            del self._sinks[device_id]

        if device_id in self._nodes:
            del self._nodes[device_id]

    @property
    def sinks(self):
        """ Yields each known sink"""
        for sink in self._sinks.values():
            yield sink

    @property
    def nodes(self):
        """ Yields each known node"""
        for node in self._nodes.values():
            yield node

    @sinks.setter
    def sinks(self, value: list):
        """ Sets a sink device """
        for sink in value:
            if sink and sink not in self._sinks:
                self._sinks[sink] = Sink(
                    device_id=sink,
                    network_id=self.network_id,
                    gateway_id=self.device_id,
                )

    @nodes.setter
    def nodes(self, value: list):
        """ Sets a node device """
        for node in value:
            if node and node not in self._nodes:
                self._nodes[node] = MeshDevice(
                    device_id=node,
                    network_id=self.network_id,
                    gateway_id=self.device_id,
                )

    def update(self, configurations: list):
        """ loops through the list of configurations and updates its sinks """
        for configuration in configurations:
            sink_id = configuration["sink_id"]
            self.sinks = [sink_id]
            self._sinks[sink_id].update(configuration)

    def notify_sinks(self, sink_id, dest, src_ep, dst_ep, qos, payload):
        """ Placeholder method to notify all sink with a given message """

    def __str__(self):
        id_str = (
            "Gateway id: {gateway_id}\nAttached to network: {network_id}\n"
        ).format(gateway_id=self.gateway_id, network_id=self.network_id)

        sinks = list(self.sinks)
        if sinks:
            id_str = "\n{}  Sinks:\n".format(id_str)
            for sink in sinks:
                id_str = "{}    {}\n".format(id_str, sink)

        nodes = list(self.nodes)
        if nodes:
            id_str = "\n{}  Nodes:\n".format(id_str)
            for node in nodes:
                id_str = "{}    {}\n".format(id_str, node)

        return id_str
