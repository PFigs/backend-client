"""
    Network
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_backend_client.mesh.device import MeshDevice
from wirepas_backend_client.mesh.gateway import Gateway


class Network(object):
    """
    Network

    Representation of a Wirepas Mesh Network
    """

    # pylint: disable=locally-disabled, too-many-arguments, invalid-name

    name = "network"

    def __init__(self, network_id: str, gateways=None, sinks=None, nodes=None):
        super(Network, self).__init__()
        self._network_id = network_id
        self._gateways = dict()

        if gateways:
            for gateway in gateways:
                self.add(gateway=gateway, sinks=sinks, nodes=nodes)

    @property
    def network_id(self):
        """ Returns the network id """
        return self._network_id

    @property
    def gateways(self):
        """ Yields the gateways dictionary """
        yield self._gateways

    @property
    def nodes(self):
        """ Loops through all gateways and returns all the known nodes """
        for gateway in self._gateways.values():
            for node in gateway.nodes:
                yield node

    @property
    def sinks(self):
        """ Loops through all gateways and returns all the known sinks """
        for gateway in self._gateways.values():
            for sink in gateway.sinks:
                yield sink

    @property
    def devices(self):
        """ Returns a dictionary of network ids and gateways """
        return {str(self._network_id): self._gateways}

    def add(self, gateway: MeshDevice, sinks: list, nodes: list):
        """ Adds devices in the network """
        gateway_id = str(gateway.device_id)
        self._gateways[gateway_id] = gateway

        if sinks:
            self._gateways[gateway_id].sinks = sinks

        if nodes:
            self._gateways[gateway_id].nodes = nodes

    def update(self, gateway_id, sink_configuration: dict):
        """ updates the inner setting of the gateway device """
        if gateway_id not in self._gateways:
            gateway_device = Gateway(gateway_id)
            self._gateways[gateway_id] = gateway_device
        self._gateways[gateway_id].update([sink_configuration])

    def remove(self, device_id: str):
        """ Removes a device from all gateways """
        for gateway in self._gateways.values():
            gateway.remove(device_id)

        if device_id in self._gateways:
            del self._gateways[device_id]

    def __str__(self):
        """ Provides a string with the summary of its contents """

        id_str = "Network: {}\n".format(self._network_id)

        for gateway_id, gateway in self._gateways.items():
            id_str = "{}  Gateway: {}\n".format(id_str, gateway_id)

            sinks = gateway.sinks
            for sink in sinks:
                id_str = "{}    Sink:{}\n".format(id_str, sink.device_id)

            nodes = gateway.nodes
            for node in nodes:
                id_str = "{}    Node:{}\n".format(id_str, node.device_id)

        return id_str
