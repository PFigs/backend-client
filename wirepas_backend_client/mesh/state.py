"""
    State
    =====

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_backend_client.mesh.gateway import Gateway
from wirepas_backend_client.mesh.network import Network


class MeshManagement(object):
    """
    MeshManagement

    Manages the Wirepas Mesh Layer

    Attributes:
        gateways (dict): a dictionary with all the existing gateways
        networks (dict): a dictionary with all the available networks
    """

    # pylint: disable=locally-disabled, invalid-name

    def __init__(self):
        super(MeshManagement, self).__init__()
        self._gateways = (
            dict()
        )  # holds gateways because they might not have a network
        self._networks = dict()

    @property
    def networks(self):
        """ yields all known networks """
        if not self._networks:
            yield list()
        for network in self._networks.values():
            yield network

    @property
    def gateways(self):
        """ yields all known gateways """
        if not self._gateways:
            yield list()
        for gateway in self._gateways.values():
            yield gateway

    @property
    def sinks(self):
        """ yields all known sinks """
        if not self._networks:
            yield list()
        for network in self._networks:  # generator magic
            for sink in self._networks[network].sinks:
                yield sink

    @property
    def nodes(self):
        """ yields all known nodes """
        if not self._networks:
            yield list()
        for network in self._networks:  # generator magic
            for node in self._networks[network].nodes:
                yield node

    def add(
        self,
        gw_id: str,
        network_id: str = None,
        sink_id: str = None,
        node_id: str = None,
        **kwargs
    ):
        """
        Creates a device entry in the node management.

        The internal dictionary is organized according to the device type

        Args:
            identifier (str): device id
            device_type (str): type of the device (Gateway, Sink, ..)
            kwargs (dict): arguments to pass on to the class constructor

        Returns:
            the created object
        """

        try:
            gateway_device = self._gateways[gw_id]
        except KeyError:
            gateway_device = Gateway(gw_id, **kwargs)
            self._gateways[gw_id] = gateway_device

        if network_id:
            gateway_device.network_id = network_id

        if network_id is not None:
            if network_id not in self._networks:
                self._networks[network_id] = Network(
                    network_id=network_id,
                    gateways=[gateway_device],
                    sinks=[sink_id],
                    nodes=[node_id],
                    **kwargs
                )
            else:
                self._networks[network_id].add(
                    gateway=gateway_device, sinks=[sink_id], nodes=[node_id]
                )

        return gateway_device

    def update(self, gateway_id, configurations):
        """
        Receives a gateway id and a list of its configurations.

        Args:
            gateway_id (str): the gateway identifier
            configurations (list): list of configuration dictionaries
        """
        self._gateways[gateway_id].update(configurations)

        for configuration in configurations:
            network_id = configuration["network_address"]
            if network_id is not None:
                network_id = str(network_id)
                if network_id not in self._networks:
                    self._networks[network_id] = Network(
                        network_id=network_id,
                        gateways=[self._gateways[gateway_id]],
                    )
                else:
                    self._networks[network_id].update(
                        gateway_id=gateway_id, sink_configuration=configuration
                    )

    def add_from_mqtt_topic(self, topic: list, node_id: list = None):
        """
        Receives a ordered topic list split at the / delimiter and a node id
        if it refers to a data message

        Args:
            topic (str): the MQTT topic
            node_id (str): the identifier of the node who sent the message
        """

        sink_id = None
        gateway_id = None
        network_id = None

        try:
            gateway_id = topic[2]
            sink_id = topic[3]
            network_id = topic[4]
        except IndexError:
            pass

        self.add(
            gw_id=gateway_id,
            network_id=network_id,
            sink_id=sink_id,
            node_id=node_id,
        )

    def remove(self, device_id):
        """ Removes a device or a network interely"""

        if device_id in self._gateways:
            del self._gateways[device_id]

        for network in self._networks.values():
            if device_id in network:
                network.remove(device_id)

    def __str__(self):
        obj = ""

        for _, v in self._networks.items():
            obj = "{}{}\n".format(obj, str(v))

        return obj
