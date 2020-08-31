"""
    MQTT Handlers
    ==============

    Contains class to handle MQTT requests

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import logging
import multiprocessing
import queue

from wirepas_backend_client.api.mqtt.connectors import MQTT
from wirepas_backend_client.api.mqtt.decorators import decode_topic_message
from wirepas_backend_client.api.mqtt.mqtt_options import MQTTqosOptions
from wirepas_backend_client.api.stream import StreamObserver
from wirepas_backend_client.tools import Settings


class MQTTObserver(StreamObserver):
    """
    MQTTObserver

    This class acts a wrapper for the MQTT connector, containing the
    primitives to setup a subscription list and handlers to act on that
    data.

    """

    def __init__(
        self,
        mqtt_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        allowed_endpoints: set = None,
        message_subscribe_handlers: dict = None,
        publish_cb: callable = None,
        logger=None,
    ) -> "MQTTObserver":
        """ MQTT Observer constructor """
        super(MQTTObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        if message_subscribe_handlers is None:
            self.message_subscribe_handlers = {"#": self.simple_mqtt_print}
        else:
            self.message_subscribe_handlers = message_subscribe_handlers

        if publish_cb is None:
            self.publish_cb = self.generate_data_send_cb()
        else:
            self.publish_cb = publish_cb

        self.mqtt = MQTT(
            username=mqtt_settings.username,
            password=mqtt_settings.password,
            hostname=mqtt_settings.hostname,
            port=mqtt_settings.port,
            ca_certs=mqtt_settings.ca_certs,
            userdata=mqtt_settings.userdata,
            transport=mqtt_settings.transport,
            clean_session=mqtt_settings.clean_session,
            reconnect_min_delay=mqtt_settings.reconnect_min_delay,
            reconnect_max_delay=mqtt_settings.reconnect_max_delay,
            allow_untrusted=mqtt_settings.allow_untrusted,
            force_unsecure=mqtt_settings.force_unsecure,
            heartbeat=mqtt_settings.heartbeat,
            keep_alive=mqtt_settings.keep_alive,
            exit_signal=self.exit_signal,
            message_subscribe_handlers=message_subscribe_handlers,
            publish_cb=self.publish_cb,
            logger=self.logger,
        )

        self.timeout = mqtt_settings.heartbeat

        if allowed_endpoints is None:
            self.allowed_endpoints = set()
        else:
            self.allowed_endpoints = allowed_endpoints

    @staticmethod
    @decode_topic_message
    def simple_mqtt_print(message, topic):
        """ Simple example to outpu topic and message contents """
        print("MQTTObserver | {} >> {}".format("/".join(topic), message))

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """

        @decode_topic_message
        def on_data_received(message, topic_items):
            """ Retrieves a MQTT message and sends it to the tx_queue """

            if not self.allowed_endpoints or (
                message.source_endpoint in self.allowed_endpoints
                and message.destination_endpoint in self.allowed_endpoints
            ):

                if self.start_signal.is_set():
                    self.logger.debug("sending message %s", message)
                    self.tx_queue.put(message)
                else:
                    self.logger.debug("waiting for manager readiness")

        return on_data_received

    def send_data(self, timeout, block):
        """
        Send_data awaits for a message in the request (rx) queue.

        The message consists of a dictionary with the following contents
        topic, qos, retain, wait_for_publish, data

        """

        try:
            message = self.rx_queue.get(timeout=timeout, block=block)
        except queue.Empty:
            return False

        qos = MQTTqosOptions.exactly_once.value
        retain = False
        wait_for_publish = False
        data = None
        topic = None

        if "topic" in message:
            topic = message["topic"]

        if "qos" in message:
            qos = message["qos"]

        if "retain" in message:
            retain = message["retain"]

        if "wait_for_publish" in message:
            wait_for_publish = message["wait_for_publish"]

        if "data" in message:
            try:
                data = message["data"].payload
            except AttributeError:
                data = message["data"]
            except TypeError:
                data = None
            except Exception:
                data = None

        if data is not None and topic is not None:
            self.mqtt.send(
                message=data,
                retain=retain,
                qos=qos,
                topic=topic,
                wait_for_publish=wait_for_publish,
            )
            return True

        return False

    def run(self):
        """
        Executes MQTT loop
        """
        self.mqtt.subscribe_messages(self.message_subscribe_handlers)
        self.mqtt.serve()
