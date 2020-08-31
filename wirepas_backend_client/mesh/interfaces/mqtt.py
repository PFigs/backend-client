"""
    NetworkDiscovery
    =================

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import logging

from wirepas_backend_client.mesh.state import MeshManagement
from wirepas_backend_client.api.mqtt import (
    MQTTObserver,
    Topics,
    decode_topic_message,
    topic_message,
)
from wirepas_backend_client.tools import Signal
from threading import Timer
from queue import Queue


class NetworkDiscovery(MQTTObserver):
    """
    NetworkDiscovery

    Tracks the MQTT topics and generates an object representation of the
    devices present in a given network.

    It builds a map of gateways, sinks and devices.

    """

    def __init__(
        self,
        mqtt_settings,
        shared_state=None,
        data_queue=None,
        event_queue=None,
        gateway_id: str = "+",
        sink_id: str = "+",
        network_id: str = "+",
        source_endpoint: str = "+",
        destination_endpoint: str = "+",
        message_subscribe_handlers=None,
        publish_cb=None,
        network_parameters=None,
        **kwargs,
    ):

        try:
            tx_queue = kwargs["tx_queue"]
        except KeyError:
            tx_queue = None

        try:
            rx_queue = kwargs["rx_queue"]
        except KeyError:
            rx_queue = None

        try:
            logger = kwargs["logger"]
        except KeyError:
            logger = logging.getLogger(__name__)

        try:
            exit_signal = kwargs["exit_signal"]
        except KeyError:
            exit_signal = Signal(False)

        try:
            start_signal = kwargs["start_signal"]
        except KeyError:
            start_signal = Signal(True)

        try:
            allowed_endpoints = kwargs["allowed_endpoints"]
        except KeyError:
            allowed_endpoints = None

        # create subscription list for MQTT API
        self.mqtt_settings = mqtt_settings
        self.mqtt_topics = Topics()

        if network_parameters:
            self.network_parameters = network_parameters
        else:
            self.network_parameters = dict(
                gw_id=str(gateway_id),
                sink_id=str(sink_id),
                network_id=str(network_id),
                src_ep=str(source_endpoint),
                dst_ep=str(destination_endpoint),
            )

        if message_subscribe_handlers:
            self.message_subscribe_handlers = message_subscribe_handlers
        else:
            self.message_subscribe_handlers = self.build_subscription()

        super(NetworkDiscovery, self).__init__(
            mqtt_settings=mqtt_settings,
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
            allowed_endpoints=allowed_endpoints,
            message_subscribe_handlers=self.message_subscribe_handlers,
            publish_cb=publish_cb,
            logger=logger,
        )

        # This is to mimic the API style in terms of having a data, event
        # and request response path
        self.response_queue = self.tx_queue
        self.request_queue = self.rx_queue
        self.data_queue = data_queue
        self.event_queue = event_queue

        self.shared_state = shared_state
        self.device_manager = MeshManagement()
        self._debug_comms = False
        self._perioidicTimer = None  # Set on notify where context is right
        self._timerRunning: bool = False  # picklable
        self.data_event_flush_timer_interval_sec: float = 1.0

        self._data_event_tx_queue = Queue()

    def __data_event_perioid_flush_timeout(self):

        txList: list = []
        while self._data_event_tx_queue.empty() is False:
            msg = self._data_event_tx_queue.get(True)
            txList.append(msg)
            self._data_event_tx_queue.task_done()
        if len(txList) > 0:
            self.data_queue.put(txList)

        self._perioidicTimer = Timer(
            self.data_event_flush_timer_interval_sec,
            self.__data_event_perioid_flush_timeout,
        ).start()

    def notify(self, message, path="response"):

        """ Puts the device on the queue"""

        if self.shared_state:
            self.shared_state["devices"] = self.device_manager

        if message:
            if "response" in path:
                self.response_queue.put(message)

            elif "data" in path and self.data_queue:
                # Data message rate is huge compared others. Handle it
                # different way

                # Put data to internal queue first.
                self._data_event_tx_queue.put(message)

                # Start on this call context.
                if self._timerRunning is False:
                    self._timerRunning = True
                    self._perioidicTimer = Timer(
                        self.data_event_flush_timer_interval_sec,
                        self.__data_event_perioid_flush_timeout,
                    ).start()

            elif "event" in path and self.event_queue:
                self.event_queue.put(message)

    def build_subscription(self):
        """
            Uses the network parameters to build a dictionary with
            topics as keys and callbacks as handlers.
        """

        # track gateway events
        event_status = self.mqtt_topics.event(
            "status", **self.network_parameters
        )
        event_received_data = self.mqtt_topics.event(
            "received_data", **self.network_parameters
        )

        response_get_configs = self.mqtt_topics.response(
            "get_configs", **self.network_parameters
        )
        response_set_config = self.mqtt_topics.response(
            "set_config", **self.network_parameters
        )
        response_send_data = self.mqtt_topics.response(
            "send_data", **self.network_parameters
        )
        response_otap_status = self.mqtt_topics.response(
            "otap_status", **self.network_parameters
        )
        response_otap_load_scratchpad = self.mqtt_topics.response(
            "otap_load_scratchpad", **self.network_parameters
        )
        response_otap_process_scratchpad = self.mqtt_topics.response(
            "otap_process_scratchpad", **self.network_parameters
        )

        message_subscribe_handlers = {
            event_status: self.generate_gateway_status_event_cb(),
            event_received_data: self.generate_gateway_data_event_cb(),
            response_get_configs: self.generate_gateway_response_get_configs_cb(),
            response_set_config: self.generate_gateway_response_set_config_cb(),
            response_send_data: self.generate_gateway_data_response_cb(),
            response_otap_status: self.generate_gateway_otap_status_response_cb(),
            response_otap_load_scratchpad: self.generate_gateway_load_scratchpad_response_cb(),
            response_otap_process_scratchpad: self.generate_gateway_process_scratchpad_response_cb(),
        }

        return message_subscribe_handlers

    # Publishing
    def send_data(self, timeout: int, block: bool):
        """ Callback provided by the interface's cb generator
            Args:
        """

        ret = super(NetworkDiscovery, self).send_data(
            timeout=timeout, block=block
        )
        if ret is not None:
            try:
                if self.shared_state:
                    if self.shared_state["devices"] is not None:
                        self.device_manager = self.shared_state["devices"]
            except KeyError:
                pass

    # Subscribing
    def generate_gateway_status_event_cb(self) -> callable:
        """ Returns a callback to handle a gateway status event """

        @topic_message
        def on_gateway_status_event_cb(payload, topic: list):
            """ Decodes an incoming gateway status event """

            message = self.mqtt_topics.constructor(
                "event", "status"
            ).from_payload(payload)
            gateway = self.device_manager.add(message.gw_id)
            gateway.state = message.state
            self.notify(message=message, path="event")

        return on_gateway_status_event_cb

    def generate_gateway_data_event_cb(self) -> callable:
        """ Returns a callback to handle a gateway data event """

        @decode_topic_message
        def on_gateway_data_event_cb(data_message, topic: list):
            """ Decodes an incoming data event callback """
            if self._debug_comms:
                self.logger.debug("data event: %s", data_message)

            self.device_manager.add_from_mqtt_topic(
                topic, data_message.source_address
            )
            self.notify(message=data_message, path="data")

        return on_gateway_data_event_cb

    def generate_gateway_response_get_configs_cb(self) -> callable:
        """ Returns a callback to handle a
        response with gateway configurations """

        @topic_message
        def on_gateway_get_configs_cb(payload, topic: list):
            """ Decodes and incoming configuration response """

            if self._debug_comms:
                self.logger.debug("configs response: %s", payload)

            message = self.mqtt_topics.constructor(
                "response", "get_configs"
            ).from_payload(payload)

            self.device_manager.add_from_mqtt_topic(topic)
            self.device_manager.update(message.gw_id, message.configs)
            self.notify(message, path="response")

        return on_gateway_get_configs_cb

    def generate_gateway_otap_status_response_cb(self) -> callable:
        """ Returns a callback to handle otap status responses """

        @topic_message
        def on_gateway_otap_status_cb(payload, topic: list):
            """ Decodes an otap status response """
            if self._debug_comms:
                self.logger.debug("otap status response: %s", payload)

            message = self.mqtt_topics.constructor(
                "response", "otap_status"
            ).from_payload(payload)
            self.notify(message, path="response")

        return on_gateway_otap_status_cb

    def generate_gateway_response_set_config_cb(self) -> callable:
        """ Returns a callback to handle
        responses to configuration set requests """

        @topic_message
        def on_gateway_set_config_response_cb(payload, topic: list):
            """ Decodes a set config response """
            if self._debug_comms:
                self.logger.debug("set config response: %s", payload)

            message = self.mqtt_topics.constructor(
                "response", "set_config"
            ).from_payload(payload)
            self.notify(message, path="response")

        return on_gateway_set_config_response_cb

    def generate_gateway_data_response_cb(self) -> callable:
        """ Returns a callback to handle data responses """

        @topic_message
        def on_gateway_data_response_cb(payload, topic: list):
            """ Decodes a data response """
            if self._debug_comms:
                self.logger.debug("send data response: %s", payload)

            self.device_manager.add_from_mqtt_topic(topic)
            message = self.mqtt_topics.constructor(
                "response", "send_data"
            ).from_payload(payload)

            self.notify(message, path="response")

        return on_gateway_data_response_cb

    def generate_gateway_load_scratchpad_response_cb(self) -> callable:
        """ Returns a callback to handle the
        loading of a scratchpad into the target sink """

        @topic_message
        def on_gateway_load_scratchpad_response_cb(payload, topic: list):
            """ """
            if self._debug_comms:
                self.logger.debug("load scratchpad response: %s", payload)

            message = self.mqtt_topics.constructor(
                "response", "otap_load_scratchpad"
            ).from_payload(payload)
            self.notify(message, path="response")

        return on_gateway_load_scratchpad_response_cb

    def generate_gateway_process_scratchpad_response_cb(self) -> callable:
        """ Returns a callback to handle a processed scratchpad response """

        @topic_message
        def on_gateway_process_scratchpad_cb(payload, topic: list):
            """ """
            if self._debug_comms:
                self.logger.debug("process scratchpad response: %s", payload)
            message = self.mqtt_topics.constructor(
                "response", "otap_process_scratchpad"
            ).from_payload(payload)
            self.notify(message, path="response")

        return on_gateway_process_scratchpad_cb
