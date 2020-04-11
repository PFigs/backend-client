"""
    HTTP API
    ============

    Creates a HTTP server and handles incoming requests to the
    gateway MQTT api.

    Please use the MQTT api whenever possible.

    gateways_and_sinks has following scheme:
    { 'gw_id':
        {'sink_id':
            {# Following fields from item of
             # gw-response/get_configs->configs[]
             'started': True/False,
             'app_config_seq': int,
             'app_config_diag': int,
             'app_config_data': bytes,
             'node_address' : int,
             # Internal field for monitoring sink's presense
             'present': True/False
            }
        }
    }

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
from enum import Enum
from threading import Thread
import binascii
import http.server
import logging
import multiprocessing
import queue
import time
import urllib

from wirepas_backend_client.api.mqtt import Topics
from wirepas_backend_client.api.mqtt import MQTT_QOS_options
from wirepas_backend_client.api.stream import StreamObserver
from wirepas_backend_client.tools import Settings


class App_config_keys(Enum):
    app_config_data_key = "app_config_data"
    app_config_diag_key = "app_config_diag"
    app_config_node_address_key = "node_address"
    app_config_node_network_address_key = "network_address"
    app_config_seq_key = "app_config_seq"
    app_config_sink_id_key = "sink_id"
    app_config_started_key = "started"
    sink_item_present_key = "present"


class SinkAndGatewayStatusObserver(Thread):
    """ SinkAndGatewayStatusObserver """

    def __init__(self, exit_signal, gw_status_queue, logger):
        super(SinkAndGatewayStatusObserver, self).__init__()
        self.exit_signal = exit_signal
        self.gw_status_queue = gw_status_queue
        self.logger = logger
        self.gateways_and_sinks = (
            {}
        )  # This will be populated according query defined in
        # settins.yaml/mqtt_subscribe_network_id.

        # pylint: disable=locally-disabled, too-many-nested-blocks,
        # too-many-branches

    def run(self):
        while not self.exit_signal.is_set():
            try:
                # Http server does not subscribe MQTT configuration. It is
                # done by caller of http. Caller subscribes certain network
                # all gateways.

                status_msg = self.gw_status_queue.get(block=True, timeout=60)
                self.logger.info("HTTP status_msg={}".format(status_msg))
                # New status of gateway received.
                if status_msg["gw_id"] not in self.gateways_and_sinks:
                    # New gateway detected
                    self.gateways_and_sinks[status_msg["gw_id"]] = {}

                # Initially mark all sinks of this gateway as not present
                for sink_id, sink in self.gateways_and_sinks[
                    status_msg["gw_id"]
                ].items():
                    sink[App_config_keys.sink_item_present_key.value] = False

                for config in status_msg["configs"]:

                    # Check that mandatory field sink_id is present in message
                    if App_config_keys.app_config_sink_id_key.value in config:

                        if (
                            config[
                                App_config_keys.app_config_sink_id_key.value
                            ]
                            not in self.gateways_and_sinks[status_msg["gw_id"]]
                        ):
                            # New sink detected
                            self.gateways_and_sinks[status_msg["gw_id"]][
                                config[
                                    App_config_keys.app_config_sink_id_key.value
                                ]
                            ] = {}

                        sink = self.gateways_and_sinks[status_msg["gw_id"]][
                            config[
                                App_config_keys.app_config_sink_id_key.value
                            ]
                        ]

                        if (
                            App_config_keys.app_config_started_key.value
                            in config
                            and App_config_keys.app_config_seq_key.value
                            in config
                            and App_config_keys.app_config_diag_key.value
                            in config
                            and App_config_keys.app_config_data_key.value
                            in config
                            and App_config_keys.app_config_node_address_key.value
                            in config
                        ):
                            # All mandatory fields are present

                            sink[
                                App_config_keys.app_config_started_key.value
                            ] = config[
                                App_config_keys.app_config_started_key.value
                            ]
                            sink[
                                App_config_keys.app_config_seq_key.value
                            ] = config[
                                App_config_keys.app_config_seq_key.value
                            ]
                            sink[
                                App_config_keys.app_config_diag_key.value
                            ] = config[
                                App_config_keys.app_config_diag_key.value
                            ]
                            sink[
                                App_config_keys.app_config_data_key.value
                            ] = config[
                                App_config_keys.app_config_data_key.value
                            ]
                            sink[
                                App_config_keys.app_config_node_address_key.value
                            ] = config[
                                App_config_keys.app_config_node_address_key.value
                            ]
                            sink[
                                App_config_keys.sink_item_present_key.value
                            ] = True
                        else:
                            # There are missing fields.
                            self.handle_missing_fields(status_msg)

                            self.check_and_refresh_sink(sink)

                # Remove those sinks that are not present in this gateway
                # Cannot delete sink while iterating gateways_and_sinks dict,
                # thus create separate list for sinks to be deleted.
                self.remove_inactive_sinks(status_msg)

            except queue.Empty:
                self.logger.info("HTTP status_msg receiver running")

    def remove_inactive_sinks(self, status_msg):
        delete = []
        for sink_id, sink in self.gateways_and_sinks[
            status_msg["gw_id"]
        ].items():
            if not sink[App_config_keys.sink_item_present_key.value]:
                delete.append(sink_id)
                self.logger.warning(
                    "sink {}/{} is removed".format(
                        status_msg["gw_id"], sink_id
                    )
                )
        # And delete those sinks in separate loop.
        for i in delete:
            del self.gateways_and_sinks[status_msg["gw_id"]][i]
        self.logger.info(
            "HTTP Server gateways_and_sinks={}".format(self.gateways_and_sinks)
        )

    def check_and_refresh_sink(self, sink):
        if "started" in sink:
            # Sink has been present before, rely on old values
            # and keep this sink in the configuration.
            sink[App_config_keys.sink_item_present_key.value] = True
        else:
            sink[App_config_keys.sink_item_present_key.value] = False

    def handle_missing_fields(self, status_msg):
        self.logger.warning(
            "Mandatory fields missing from "
            " gw-response/get_configs: {}".format(status_msg)
        )


class HTTPSettings(Settings):
    """HTTP Settings"""

    _MANDATORY_FIELDS = ["http_host", "http_port"]

    def __init__(self, settings: Settings) -> "HTTPSettings":
        self.http_host = None
        self.http_port = None

        super(HTTPSettings, self).__init__(settings)

        self.hostname = self.http_host
        self.port = self.http_port


class ConnectionServer(http.server.ThreadingHTTPServer):
    """ ConnectionServer """

    # pylint: disable=locally-disabled, too-many-arguments

    close_connection = False
    request_queue_size = 10000
    allow_reuse_address = True
    server_time_out_secs = 600
    protocol_version = "HTTP/1.1"

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        bind_and_activate=True,
        logger=None,
        http_tx_queue=None,
        status_observer=None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.http_tx_queue = http_tx_queue
        self.status_observer = status_observer

        super(ConnectionServer, self).__init__(
            server_address, RequestHandlerClass, bind_and_activate
        )

    def get_request(self):
        """Get the request and client address from the socket.

        May be overridden.

        """
        try:
            value = self.socket.accept()
        except Exception as err:
            print("socket accept exception: {}".format(err))
            value = None
        return value


class HTTPObserver(StreamObserver):
    """
    HTTPObserver has three Observer functions:
    monitors the web traffic and sends requests to mqtt broker,
    monitors mqtt messages about sending status (not implemented ### TODO ###),
    monitors what gateways and sinks are online.
    """

    # pylint: disable=locally-disabled, too-many-arguments, broad-except,
    # unused-argument
    def __init__(
        self,
        http_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        gw_status_queue: multiprocessing.Queue,
        request_wait_timeout: int = 600,
        close_connection: bool = False,
        request_queue_size: int = 1000,
        allow_reuse_address: bool = True,
        logger=None,
    ) -> "HTTPObserver":
        super(HTTPObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.port = http_settings.port
        self.hostname = http_settings.hostname
        self.gw_status_queue = gw_status_queue
        self.http_tx_queue = tx_queue

        self.status_observer = SinkAndGatewayStatusObserver(
            self.exit_signal, self.gw_status_queue, self.logger
        )

        while not self.exit_signal.is_set():
            try:
                # Crate the HTTP server.
                self.httpd = ConnectionServer(
                    (self.hostname, self.port),
                    wbcHTTPRequestHandler,
                    bind_and_activate=True,
                    logger=self.logger,
                    http_tx_queue=self.http_tx_queue,
                    status_observer=self.status_observer,
                )

                self.httpd.request_wait_timeout = request_wait_timeout
                self.httpd.close_connection = close_connection
                self.httpd.request_queue_size = request_queue_size
                self.httpd.allow_reuse_address = allow_reuse_address
                self.logger.info(
                    "HTTP Server is serving at port: %s", self.port
                )
                break

            except Exception as ex:
                self.logger.error(
                    "ERROR: Opening HTTP Server port %s failed. Reason: %s. "
                    "Retrying after 10 seconds.",
                    self.port,
                    ex,
                )
                time.sleep(10)

    def run(self):
        """ main loop: starts status observer thread """
        self.status_observer.start()

        # Run until killed.
        try:
            while not self.exit_signal.is_set():
                # Handle a http request.
                self.logger.info("Waiting for next request")
                self.httpd.handle_request()
        except Exception as err:
            self.logger.exception(err)

        self.httpd.server_close()
        self.logger.info("HTTP Control server killed")
        self.status_observer.join()

    def kill(self):
        """Kill the gateway thread.
        """

        # Send a dummy request to let the handle_request to proceed.
        urllib.request.urlopen(
            "http://{}:{}".format(self.hostname, self.port)
        ).read()


class wbcHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A simple HTTP server class.

    Only overrides the do_GET from the HTTP server so it catches
    all the GET requests and processes them into commands.
    """

    class HTTP_response_fields(Enum):
        path = "path"
        params = "params"
        gw_and_sinks = "gateways_and_sinks"
        command = "command"
        text = "text"
        code = "code"

    class HTTP_server_commands(Enum):
        data_tx = "datatx"
        start = "start"
        stop = "stop"
        set_config = "setconfig"
        get_info = "info"

    class HTTP_server_response_codes(Enum):
        http_response_ok = 200
        http_response_code_unknown_command = 500

    # pylint: disable=locally-disabled, too-many-arguments, broad-except,
    # unused-argument, invalid-name
    # pylint: disable=locally-disabled, too-many-statements, too-many-locals,
    # too-many-branches, too-many-nested-blocks

    def __init__(self, request, client_address, server):
        #
        self.logger = server.logger or logging.getLogger(__name__)
        self.http_tx_queue = server.http_tx_queue
        self.status_observer = server.status_observer
        self.mqtt_topics = Topics()

        self.debug_comms = False  # if true communication details are logged
        self.http_api_test_mode = False  # When on, does not send MQTT messages

        super(wbcHTTPRequestHandler, self).__init__(
            request, client_address, server
        )

    def end_headers(self):
        self.send_my_headers()
        super().end_headers()

    def send_my_headers(self):
        self.send_header(
            "Cache-Control", "no-cache, no-store, must-revalidate"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _process_request(self, verb):
        """ Decodes an incoming http request regardless of its verb"""
        __default_command = "info"

        # Parse into commands and parameters
        slitted = urllib.parse.urlsplit(self.path)
        params = dict(
            urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)
        )
        try:
            command = slitted.path.split("/")[1]
        except KeyError:
            command = __default_command

        if command == "":
            command = __default_command
        if self.debug_comms is True:
            self.logger.info(
                dict(
                    protocol="http",
                    verb=verb,
                    path=self.path,
                    params=str(params),
                    command=command,
                    gateways_and_sinks=str(
                        self.status_observer.gateways_and_sinks
                    ),
                )
            )

        self._mesh_control(command, params)

    # flake8: noqa
    def do_GET(self):
        """Process a single HTTP GET request.
        """
        self._process_request("GET")

    def do_POST(self):
        """Process a single HTTP POST request.
        """
        self._process_request("POST")

    def _mesh_control(self, command, params):
        """ Decodes an incoming payload and acts upon it """

        # By default assume that gateway configuration does not need
        # refreshing after command is executed
        refresh = False
        response = dict()

        # Create HTTP response header
        response[self.HTTP_response_fields.path.value] = self.path
        response[self.HTTP_response_fields.params.value] = str(params)
        response[self.HTTP_response_fields.gw_and_sinks.value] = str(
            self.status_observer.gateways_and_sinks
        )
        response[self.HTTP_response_fields.command.value] = command

        if len(command) > 0:

            self.logger.info("HTTP command '%s' received", command)

            response[self.HTTP_response_fields.text.value] = f"{command} ok!"
            response[
                self.HTTP_response_fields.code.value
            ] = self.HTTP_server_response_codes.http_response_ok.value

            config_messages = list()
            messages = list()

            # Go through all gateways and sinks that are currently known
            gateways_and_sinks = self.status_observer.gateways_and_sinks
            for gateway_id, sinks in gateways_and_sinks.items():

                # Sends the command towards all the discovered sinks
                for sink_id, sink in sinks.items():

                    command_was_ok = False

                    if command == self.HTTP_server_commands.data_tx.value:
                        # Handle transmit request.
                        (
                            command_was_ok,
                            new_messages,
                        ) = self._handle_datatx_command(
                            gateway_id,
                            refresh,
                            response,
                            sink,
                            sink_id,
                            command,
                            params,
                            gateways_and_sinks,
                        )
                        if command_was_ok is not True:
                            break
                        else:
                            if len(new_messages) > 0:
                                for msg in new_messages:
                                    messages.append(msg)

                    elif command == self.HTTP_server_commands.start.value:
                        (
                            command_was_ok,
                            refresh,
                            new_messages,
                        ) = self._handle_start_command(
                            gateway_id, refresh, sink_id
                        )
                        if len(new_messages) > 0:
                            for msg in new_messages:
                                messages.append(msg)
                    elif command == self.HTTP_server_commands.stop.value:
                        (
                            command_was_ok,
                            refresh,
                            new_messages,
                        ) = self._handle_stop_command(
                            gateway_id, refresh, sink_id
                        )
                        if len(new_messages) > 0:
                            for msg in new_messages:
                                messages.append(msg)
                    elif command == self.HTTP_server_commands.set_config.value:
                        (
                            command_was_ok,
                            refresh,
                            new_messages,
                        ) = self._handle_setconfig_command(
                            gateway_id, params, refresh, sink, sink_id
                        )
                        if len(new_messages) > 0:
                            for msg in new_messages:
                                messages.append(msg)
                    elif command == self.HTTP_server_commands.get_info.value:
                        (
                            command_was_ok,
                            refresh,
                            new_messages,
                        ) = self._handle_info_command(
                            command,
                            gateway_id,
                            refresh,
                            response,
                            sink,
                            sink_id,
                        )
                        if len(new_messages) > 0:
                            for msg in new_messages:
                                messages.append(msg)
                    else:
                        self._handle_unknown_command(response)
                        break
                    # Renews information about remote gateways
                    if command_was_ok is True:

                        if refresh:
                            refresh = False
                            self._send_get_config_request_to_gateways(
                                gateway_id, config_messages
                            )
                    else:
                        self.logger.error(
                            "HTTP command parsing (%s) failed", command
                        )

            # sends all messages
            if self.http_api_test_mode is False:
                if len(messages) > 0:
                    self.logger.info(
                        "Send %d MQTT data messages", len(messages)
                    )
                    self._send_messages_to_mqtt(messages)
                if len(config_messages) > 0:
                    self.logger.info(
                        "Send %d MQTT config messages", len(config_messages)
                    )
                    self._send_messages_to_mqtt(config_messages)
            else:
                self.logger.error(
                    "HTTP API test test mode. " "Not sending MQTT messages."
                )
        else:
            self._handle_empty_request(response)

        if (
            response[self.HTTP_response_fields.code.value]
            != self.HTTP_server_response_codes.http_response_ok.value
        ):
            self.logger.error(response)
        else:
            self.logger.info("HTTP command ok")

        # send code and response message
        self._send_http_response(response)

        if self.debug_comms is True:
            self.logger.info("HTTP response body: %s", response)

    def _send_http_response(self, response):
        self.send_response(
            code=response[self.HTTP_response_fields.code.value],
            message=response[self.HTTP_response_fields.text.value],
        )
        self.end_headers()

    def _handle_empty_request(self, response):

        self.logger.error("HTTP request was empty")

        response[self.HTTP_response_fields.text.value] = "Error: empty request"
        response[
            self.HTTP_response_fields.code.value
        ] = (
            self.HTTP_server_response_codes.http_response_code_unknown_command.value
        )

    def _send_get_config_request_to_gateways(self, gateway_id, messages):
        message = self.mqtt_topics.request_message(
            "get_configs", **dict(gw_id=gateway_id)
        )
        messages.append(message)

    def _send_messages_to_mqtt(self, messages):
        for message in messages:
            if len(message) > 0:
                if self.debug_comms is True:
                    self.logger.info({message["topic"]: str(message["data"])})
                self.http_tx_queue.put(message)
            else:
                self.logger.error("MQTT message size is 0")

    def _handle_unknown_command(self, response):
        response[
            self.HTTP_response_fields.code.value
        ] = (
            self.HTTP_server_response_codes.http_response_code_unknown_command.value
        )
        self.logger.error("HTTP request command was unknown")
        response[self.HTTP_response_fields.text.value] = "Unknown command"

    def _find_sink(self, sink_node_address: int, gateways: dict):

        sink_node_address_belongs_network = False
        for gateway_id, sinks in gateways.items():
            # Sends the command towards all the discovered sinks
            for sink_id, sink in sinks.items():
                if (
                    sink[App_config_keys.app_config_node_address_key.value]
                    == sink_node_address
                ):
                    sink_node_address_belongs_network = True
                    break
            if sink_node_address_belongs_network is True:
                break

        return sink_node_address_belongs_network

    def _handle_datatx_command(
        self,
        gateway_id,
        refresh,
        response,
        sink,
        sink_id,
        command,
        params,
        gateways: dict,
    ):

        command_was_ok: bool = True
        command_parse_was_ok: bool = False
        newMessages = list()
        message = None

        try:
            # When sending message to certain gateway/sink on network we need
            destination_node_address = int(params["destination"])
            src_ep = int(params["source_ep"])
            dst_ep = int(params["dest_ep"])

            # QOS passed by HTTP request (int(params["qos"])) is not used
            # from now on. MQTT QOS is fixed to
            # MQTT_QOS_options.exactly_once.value
            qos = MQTT_QOS_options.exactly_once.value

            payload = binascii.unhexlify(params["payload"])
            command_parse_was_ok = True
        except KeyError as error:
            response[
                self.HTTP_response_fields.code.value
            ] = (
                self.HTTP_server_response_codes.http_response_code_unknown_command.value
            )
            response[
                self.HTTP_response_fields.text
            ] = f"Missing field: {error}"
            command_was_ok = False
        except Exception as error:
            response[
                self.HTTP_response_fields.code.value
            ] = (
                self.HTTP_server_response_codes.http_response_code_unknown_command.value
            )
            response[
                self.HTTP_response_fields.text
            ] = f"Unknown error: {error}"
            command_was_ok = False

        if command_parse_was_ok is True:
            try:
                is_unack_csma_ca = params["fast"] in ["true", "1", "yes", "y"]
            except KeyError:
                is_unack_csma_ca = False

            try:
                hop_limit = int(params["hoplimit"])
            except KeyError:
                hop_limit = 0

            try:
                count = int(params["count"])
            except KeyError:
                count = 1

            # Expected behavior:
            # (1) If destination_node_address is any of gateway sink addresses,
            # send only to desired sink.

            # (2) If destination_node_address is not any of gateway sink
            # addresses, then send this to all sinks of gateways belonging
            # to this network

            # Assumptions
            # (1) each sink node address is unique to network

            send_message_to_sink: bool = False

            if self._find_sink(destination_node_address, gateways):
                if (
                    sink[App_config_keys.app_config_node_address_key.value]
                    == destination_node_address
                ):
                    # send only addressed sink
                    send_message_to_sink = True
                    if self.debug_comms is True:
                        self.logger.info("Node address is sink address")

            else:
                # send to all sinks on network
                send_message_to_sink = True

            if send_message_to_sink is True:
                # sends a or multiple messages according to the count
                # parameter in the request

                while count:

                    if self.debug_comms is True:
                        self.logger.info(
                            "Create message to be sent via %s/%s to "
                            "nodeaddress=%s dst ep=%s payload=%s",
                            gateway_id,
                            sink_id,
                            destination_node_address,
                            dst_ep,
                            binascii.hexlify(payload),
                        )

                    count -= 1
                    message = self.mqtt_topics.request_message(
                        "send_data",
                        **dict(
                            sink_id=sink_id,
                            gw_id=gateway_id,
                            dest_add=destination_node_address,
                            src_ep=src_ep,
                            dst_ep=dst_ep,
                            qos=qos,
                            payload=payload,
                            is_unack_csma_ca=is_unack_csma_ca,
                            hop_limit=hop_limit,
                        ),
                    )
                    newMessages.append(message)

        return command_was_ok, newMessages

    def _handle_info_command(
        self, command, gateway_id, refresh, response, sink, sink_id
    ):

        command_was_ok = True
        refresh = True
        newMessages = list()

        response[self.HTTP_response_fields.command.value] = command
        # Add rest of fields
        response["gateway"] = gateway_id
        response["sink"] = sink_id
        response["started"] = sink[
            App_config_keys.app_config_started_key.value
        ]
        response["app_config_seq"] = str(
            sink[App_config_keys.app_config_seq_key.value]
        )
        response["app_config_diag"] = str(
            sink[App_config_keys.app_config_diag_key.value]
        )
        response["app_config_data"] = str(
            sink[App_config_keys.app_config_data_key.value]
        )

        return command_was_ok, refresh, newMessages

    def _handle_setconfig_command(
        self, gateway_id, params, refresh, sink, sink_id
    ):

        command_was_ok = True
        refresh = True
        newMessages = list()

        try:
            seq = int(params["seq"])
        except KeyError:
            if sink[App_config_keys.app_config_seq_key.value] == 254:
                seq = 1
            else:
                seq = sink[App_config_keys.app_config_seq_key.value] + 1
        try:
            diag = int(params["diag"])
        except KeyError:
            diag = sink[App_config_keys.app_config_diag_key.value]
        try:
            data = bytes.fromhex(params["data"])
        except KeyError:
            data = sink[App_config_keys.app_config_data_key.value]
        new_config = dict(
            app_config_diag=diag, app_config_data=data, app_config_seq=seq
        )
        message = self.mqtt_topics.request_message(
            "set_config",
            **dict(sink_id=sink_id, gw_id=gateway_id, new_config=new_config),
        )
        newMessages.append(message)
        return command_was_ok, refresh, newMessages

    def _handle_stop_command(self, gateway_id, refresh, sink_id):

        command_was_ok = True
        refresh = True
        newMessages = list()

        new_config = dict(started=False)
        message = self.mqtt_topics.request_message(
            "set_config",
            **dict(sink_id=sink_id, gw_id=gateway_id, new_config=new_config),
        )
        newMessages.append(message)

        return command_was_ok, refresh, newMessages

    def _handle_start_command(self, gateway_id, refresh, sink_id):

        command_was_ok = True
        newMessages = list()

        new_config = dict(started=True)
        message = self.mqtt_topics.request_message(
            "set_config",
            **dict(sink_id=sink_id, gw_id=gateway_id, new_config=new_config),
        )
        newMessages.append(message)
        refresh = True
        return command_was_ok, refresh, newMessages
