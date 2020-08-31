"""
    Decorators
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from functools import wraps
import wirepas_messaging
from wirepas_backend_client.messages.interface import MessageManager


def decode_topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        try:
            topic = message.topic
            topic_items = topic.split("/")
            source_endpoint = int(topic_items[-2])
            destination_endpoint = int(topic_items[-1])
            network_id = int(topic_items[-3])
            data = MessageManager.map(
                source_endpoint, destination_endpoint
            ).from_bus(message.payload)
            data.network_id = network_id
            f(data, topic_items)
        except (
            IndexError,
            wirepas_messaging.gateway.api.wirepas_exceptions.GatewayAPIParsingException,
        ):
            f(message.payload, topic_items)

    return wrapper_retrieve_message


def topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        f(message.payload, topic)

    return wrapper_retrieve_message
