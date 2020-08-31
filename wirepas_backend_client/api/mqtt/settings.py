"""
    Settings
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# pylint: disable=locally-disabled, duplicate-code


from wirepas_backend_client.tools import Settings


class MQTTSettings(Settings):
    """
    MQTTSettings

    Argument wrapper to translate inbound to internal properties.

    """

    # username and password are not required to allow anonymous connections
    _MANDATORY_FIELDS = [
        "mqtt_username",
        "mqtt_password",
        "mqtt_hostname",
        "mqtt_port",
    ]

    def __init__(self, settings: Settings) -> "MQTTSettings":

        self.mqtt_username = None
        self.mqtt_password = None
        self.mqtt_hostname = None
        self.mqtt_port = None
        self.mqtt_persist_session = None
        self.mqtt_subscribe_network_id = None
        self.mqtt_subscribe_sink_id = None
        self.mqtt_subscribe_gateway_id = None
        self.mqtt_subscribe_source_endpoint = None
        self.mqtt_subscribe_destination_endpoint = None
        self.mqtt_ca_certs = None
        self.mqtt_ciphers = None
        self.mqtt_allow_untrusted = None
        self.mqtt_force_unsecure = None
        self.mqtt_topic = None
        self.userdata = None
        self.transport = "tcp"
        self.reconnect_min_delay = 10
        self.reconnect_max_delay = 120
        self.heartbeat = 10
        self.keep_alive = 60

        super(MQTTSettings, self).__init__(settings)

        self.username = self.mqtt_username
        self.password = self.mqtt_password
        self.hostname = self.mqtt_hostname
        self.port = self.mqtt_port
        self.clean_session = not self.mqtt_persist_session
        self.network_id = self.mqtt_subscribe_network_id
        self.sink_id = self.mqtt_subscribe_sink_id
        self.gateway_id = self.mqtt_subscribe_gateway_id
        self.source_endpoint = self.mqtt_subscribe_source_endpoint
        self.destination_endpoint = self.mqtt_subscribe_destination_endpoint
        self.ca_certs = self.mqtt_ca_certs
        self.allow_untrusted = self.mqtt_allow_untrusted
        self.force_unsecure = self.mqtt_force_unsecure
        self.ciphers = self.mqtt_ciphers
        self.topic = self.mqtt_topic

    def __str__(self):
        return super()._helper_str(key_filter="mqtt")
