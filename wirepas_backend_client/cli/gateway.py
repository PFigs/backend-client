"""
    Cli Module
    ===========

    Contains the cmd cli interface

    launch as wm-gw-cli or python -m wirepas_gateway_client.cli

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import cmd
import json

from wirepas_messaging.gateway.api import GatewayState
from wirepas_messaging.gateway.api import GatewayResultCode

from wirepas_backend_client.cli.set_diagnostics.fea_set_neighbor_diagnostics import (
    SetDiagnostics,
    SetDiagnosticsIntervals,
)
from ..api.mqtt import MQTT_QOS_options
from ..mesh.sink import Sink
from ..mesh.gateway import Gateway

import threading
from time import sleep


class GatewayCliCommands(cmd.Cmd):
    """
    GatewayCliCommands

    Implements a simple interactive cli to browse the network devices
    and send basic commands.
    """

    # pylint: disable=locally-disabled, no-member, too-many-arguments, unused-argument
    # pylint: disable=locally-disabled, too-many-boolean-expressions
    # pylint: disable=locally-disabled, invalid-name
    # pylint: disable=locally-disabled, too-many-function-args
    # pylint: disable=locally-disabled, too-many-public-methods

    def __init__(self, **kwargs):
        super().__init__()
        self.intro = (
            "Welcome to the Wirepas Gateway Client cli!\n"
            "Connecting to {mqtt_username}@{mqtt_hostname}:{mqtt_port}"
            " (unsecure: {mqtt_force_unsecure})\n\n"
            "You can now set all your command arguments using key=value!\n\n"
            "Type help or ? to list commands\n\n"
            "Type ! to escape shell commands\n"
            "Use Arrow Up/Down to navigate your command history\n"
            "Use TAB for auto complete\n"
            "Use CTRL-D, bye or q to exit\n"
        )

        self._prompt_base = "wm-gw-cli"
        self._prompt_format = "{} | {} > "
        self._display_pending_response = False
        self._display_pending_event = False
        self._display_pending_data = False
        self._selection = dict(sink=None, gateway=None, network=None)

        self._device_id_display_string_width = 16

        self._dataQueueMessageHandler = None
        self._eventQueueMessageHandler = None
        self._responseQueueMessageHandler = None

    @property
    def gateway(self):
        """
        Returns the currently selected gateway
        """
        return self._selection["gateway"]

    @property
    def sink(self):
        """
        Returns the currently selected sink
        """
        return self._selection["sink"]

    @property
    def network(self):
        """
        Returns the currently selected network
        """
        return self._selection["network"]

    def on_update_prompt(self):
        """ Updates the prompt with the gateway and sink selection """

        new_prompt = "{}".format(self._prompt_base)

        if self._selection["gateway"]:
            new_prompt = "{}:{}".format(
                new_prompt, self._selection["gateway"].device_id
            )

        if self._selection["sink"]:
            new_prompt = "{}:{}".format(
                new_prompt, self._selection["sink"].device_id
            )

        self.prompt = self._prompt_format.format(
            self.time_format(), new_prompt
        )

    def on_print(self, reply, reply_greeting=None, pretty=None):
        """ Prettified reply """
        serialization = reply
        try:
            serialization = reply.serialize()
            print(
                f"{self._reply_greeting} {serialization['gw_id']}"
                f"/{serialization['sink_id']}"
                f"/{serialization['network_id']}"
                f"|{serialization['source_endpoint']}"
                f"->{serialization['destination_endpoint']}"
                f"@{serialization['tx_time']}"
            )
        except AttributeError:
            serialization = None

        if self._minimal_prints:
            return

        indent = None
        if pretty or self._pretty_prints:
            indent = 4

        if serialization:
            print(json.dumps(serialization, indent=indent))
        else:
            print(reply)

    def set_message_handlers(
        self,
        dataQueueMessageHandler,
        eventQueueMessageHandler,
        responseQueueMessageHandler,
    ):
        """ Set message handlers that process incoming messages """
        self._dataQueueMessageHandler = dataQueueMessageHandler
        self._eventQueueMessageHandler = eventQueueMessageHandler
        self._responseQueueMessageHandler = responseQueueMessageHandler

    def _clear_message_handlers(self):
        """ Clear message handlers """
        self._dataQueueMessageHandler = None
        self._eventQueueMessageHandler = None
        self._responseQueueMessageHandler = None

    def on_response_queue_message(self, message):
        """ Method called when retrieving a message from the response queue """
        if self._responseQueueMessageHandler is not None:
            self._responseQueueMessageHandler(message)

        if self._display_pending_response:
            self.on_print(message, "Pending response message <<")

    def on_data_queue_message(self, message):
        """ Method called when retrieving a message from the data queue """
        if self._dataQueueMessageHandler is not None:
            self._dataQueueMessageHandler(message)

        if self._display_pending_data:
            self.on_print(message, "Pending data message <<")

    def on_event_queue_message(self, message):
        """ Method called when retrieving a message from the event queue """
        if self._eventQueueMessageHandler is not None:
            self._eventQueueMessageHandler(message)

        if self._display_pending_event:
            self.on_print(message, "Pending event message <<")

    def do_toggle_print_pending_responses(self, line):
        """
        When True prints any response that is going to be discarded
        """
        self._display_pending_response = not self._display_pending_response
        print(
            "display pending responses: {}".format(
                self._display_pending_response
            )
        )

    def do_toggle_print_pending_events(self, line):
        """
        When True prints any event that is going to be discarded
        """
        self._display_pending_event = not self._display_pending_event
        print("display pending events: {}".format(self._display_pending_event))

    def do_toggle_print_pending_data(self, line):
        """
        When True prints any data that is going to be discarded
        """
        self._display_pending_data = not self._display_pending_data
        print("display pending events: {}".format(self._display_pending_data))

    # track status
    def do_track_devices(self, line):
        """
        Displays the current selected devices for the desired amount of time.

        A key press will exit the loop.

        Usage:
            track_devices argument=value

        Arguments:
            - iterations=Inf
            - update_rate=1
            - silent=False

        Returns:
            Prints the current known devices
        """
        options = dict(
            iterations=dict(type=int, default=float("Inf")),
            update_rate=dict(type=int, default=1),
            silent=dict(type=bool, default=None),
        )

        args = self.retrieve_args(line, options)

        self._tracking_loop(self.do_list, **args)

    def do_track_data_packets(self, line):
        """
        Displays the incoming packets for one / all devices.

        A newline will exit the tracking loop

        Usage:
            track_data_packets argument=value

        Arguments:
            - gw_id=None
            - sink_id=None
            - network_id=None # filter by network
            - source_address=None
            - source_endpoint=None
            - destination_endpoint=None
            - iterations=Inf
            - update_rate=1 # period to print status if no message is acquired
            - show_events=False # will display answers as well
            - silent=False # when True the loop number is not printed

        Returns:
            Prints
        """

        options = dict(
            gw_id=dict(type=str, default=None),
            sink_id=dict(type=str, default=None),
            network_id=dict(type=int, default=None),
            source_address=dict(type=int, default=None),
            source_endpoint=dict(type=int, default=None),
            destination_endpoint=dict(type=int, default=None),
            iterations=dict(type=int, default=float("Inf")),
            update_rate=dict(type=int, default=1),
            show_events=dict(type=bool, default=False),
            silent=dict(type=bool, default=False),
        )

        args = self.retrieve_args(line, options)
        args["cli"] = self

        def handler_cb(cli, **kwargs):

            source_address = kwargs.get("source_address", None)
            source_endpoint = kwargs.get("source_endpoint", None)
            destination_endpoint = kwargs.get("destination_endpoint", None)
            network_id = kwargs.get("network_id", None)
            gw_id = kwargs.get("gw_id", None)
            sink_id = kwargs.get("sink_id", None)
            show_events = kwargs.get("show_events", None)

            def print_on_match(message):
                if (
                    cli.is_match(message, "gw_id", gw_id)
                    and cli.is_match(message, "sink_id", sink_id)
                    and cli.is_match(message, "network_id", network_id)
                    and cli.is_match(message, "source_address", source_address)
                    and cli.is_match(
                        message, "source_endpoint", source_endpoint
                    )
                    and cli.is_match(
                        message, "destination_endpoint", destination_endpoint
                    )
                ):
                    cli.on_print(message)

            for message in cli.consume_data_queue():
                print_on_match(message)

            if show_events:
                for message in cli.consume_event_queue():
                    print_on_match(message)

        self._tracking_loop(cb=handler_cb, **args)

        # commands

    def do_ls(self, line):
        """
        See list
        """
        self.do_list(line)

    def helpdo_list(self, line):
        """
        Lists all known networks and devices

        Usage:
            list

        Returns:
            Prints all known nodes
        """
        self.do_networks(line)

    def do_selection(self, line):
        """
        Displays the current selected devices

        Usage:
            selection

        Returns:
            Prints the currently selected sink, gateay and network
        """
        for k, v in self._selection.items():
            print("{} : {}".format(k, v))

    def _set_target(self):
        """ utility method to call when either the gateway or sink are undefined"""
        print("Please define your target gateway and sink")
        if self.gateway is None:
            self.do_set_gateway("")

        if self.sink is None:
            self.do_set_sink("")

    def _filter_nodes_by_gateway_id(
        self, nodes_list: object, gateway_id: object
    ) -> list:
        filtered_nodes_list = list()
        for node in nodes_list:
            if node.gateway_id == gateway_id:
                filtered_nodes_list.append(node)
        return filtered_nodes_list

    def _filter_sinks_by_gateway_id(
        self, sink_list: object, gateway_id: object
    ) -> list:
        filtered_sink_list = list()
        for sink in sink_list:
            if sink.gateway_id == gateway_id:
                filtered_sink_list.append(sink)
        return filtered_sink_list

    def _filter_nodes_by_sink_id(
        self, node_list: list, gateway_id: object
    ) -> list:
        filtered_node_list = list()
        for node in node_list:
            if node.device_id == gateway_id:
                filtered_node_list.append(node)
        return filtered_node_list

    def _sort_items_by_device_id(self, device_list: list):
        sorted_list = sorted(device_list, key=lambda item: item.device_id)
        return sorted_list

    def _get_gateway_configuration(self, gateway_device_id):
        ret = None
        message = self.mqtt_topics.request_message(
            "get_configs", **dict(gw_id=gateway_device_id)
        )
        self.request_queue.put(message)
        response = self.wait_for_answer(gateway_device_id, message)
        if response.res == GatewayResultCode.GW_RES_OK:
            ret = response.configs
        else:
            pass
        return ret

    def _filter_gateway_configuration(
        self, configs: dict, sink_id: str
    ) -> dict:
        # Parameter configs should be return value of _get_gateway_configuration
        ret = None
        for config in configs:
            if config["sink_id"] == sink_id:
                ret = config
                break
        return ret

    def _lookup_node_address(self, gateway_device_id, sink_id):
        ret = None
        gwConfig = self._get_gateway_configuration(gateway_device_id)
        if gwConfig is not None:
            sinkConfig = self._filter_gateway_configuration(gwConfig, sink_id)
            if sinkConfig is not None:
                ret = sinkConfig["node_address"]
        return ret

    def do_set_sink(self, line):
        """
        Sets the sink to use with the commands

        Usage:
            set_sink [Enter for default]

        Returns:
            Prompts the user for the sink to use when building
            network requests
        """

        if self.gateway is None:
            self.do_set_gateway(line)

        try:
            sinks = list(self.device_manager.sinks)

            if not sinks:
                self.do_gateway_configuration(line="")
                sinks = list(self.device_manager.sinks)
        except TypeError:
            sinks = list()

        current_gateway_id = self.gateway.device_id

        print("Current gateway is {}".format(current_gateway_id))

        filtered_sink_list = self._filter_sinks_by_gateway_id(
            sinks, current_gateway_id
        )

        filtered_sink_list = self._sort_items_by_device_id(filtered_sink_list)

        custom_index = len(filtered_sink_list)
        if filtered_sink_list:
            list(
                map(
                    lambda sink: print(
                        f"{filtered_sink_list.index(sink)} "
                        f":{sink.device_id}"
                        f" ( {sink.network_id} )"
                    ),
                    filtered_sink_list,
                )
            )
        print(f"{custom_index} : custom sink id")
        arg = input("Please enter your sink selection [0]: ") or 0
        try:
            arg = int(arg)
            self._selection["sink"] = filtered_sink_list[arg]

        except (ValueError, IndexError):
            arg = input("Please enter your custom sink id: ")
            self._selection["sink"] = Sink(device_id=arg)
            print(f"Sink set to: {self._selection['sink']}")

    def do_set_gateway(self, line):
        """
        Sets the gateways to use with the commands

        Usage:
            set_gateway [Enter for default]

        Returns:
            Prompts the user for the gateway to use when building
            network requests
        """
        try:
            gateways = list(self.device_manager.gateways)
        except TypeError:
            gateways = list()

        gateways = self._sort_items_by_device_id(gateways)
        online_gateways = self._filter_online_gateways(gateways)

        custom_index = len(online_gateways)
        print("Listing current online gateways:")
        if online_gateways:
            list(
                map(
                    lambda gw: print(
                        f"{online_gateways.index(gw)} " f":{gw.device_id}"
                    ),
                    online_gateways,
                )
            )

        print(f"{custom_index} : custom gateway id")
        arg = input("Please enter your gateway selection [0]: ") or 0
        try:
            arg = int(arg)
            self._selection["gateway"] = online_gateways[arg]

        except (ValueError, IndexError):
            arg = input("Please enter your custom gateway id: ")
            self._selection["gateway"] = Gateway(device_id=arg)
            print(f"Gateway set to: {self._selection['gateway']}")

        # Finally reset sink selection
        self._selection["sink"] = None

    def do_clear_offline_gateways(self, line):
        """
        Removes offline gateways from the remote broker.

        Usage:
            clear_offline_gateways
        """

        gateways = list(self.device_manager.gateways)
        for gateway in gateways:
            if gateway.state.value == GatewayState.OFFLINE.value:
                message = self.mqtt_topics.event_message(
                    "clear", **dict(gw_id=gateway.device_id)
                )
                message["data"].Clear()
                message["data"] = message["data"].SerializeToString()
                message["retain"] = True

                print("sending clear for gateway {}".format(message))

                # remove from state
                self.device_manager.remove(gateway.device_id)
                self.notify()

                self.request_queue.put(message)
                continue

    def do_sinks(self, line):
        """
        Displays the available sinks

        Usage:
            sinks

        Returns:
            Prints the discovered sinks
        """

        current_gateway = self._selection["gateway"]

        if current_gateway:
            # print sinks under gateway
            filtered_sink_list = self._filter_sinks_by_gateway_id(
                self.device_manager.sinks, current_gateway.device_id
            )

            sorted_sink_list = self._sort_items_by_device_id(
                filtered_sink_list
            )

            print(
                "Printing sinks of currently set gateway '{}'".format(
                    current_gateway.device_id
                )
            )

            sinks_str: str
            sinks_str = ""
            for sink in sorted_sink_list:
                sinks_str += "{} ".format(sink.device_id)
                print(sink)

            sinks_str = sinks_str[:-1]

            if len(sinks_str) > 0:
                gw_sinks = "( {} )".format(sinks_str)
                print(gw_sinks)
            else:
                print("No sinks!")
        else:
            sorted_sink_list = self._sort_items_by_device_id(
                self.device_manager.sinks
            )

            print("Printing sinks from all gateways..")

            print(
                "sink id".ljust(self._device_id_display_string_width),
                "( gateway )",
            )

            for sink in sorted_sink_list:
                print(
                    str(sink.device_id).ljust(
                        self._device_id_display_string_width
                    ),
                    "( {} )".format(sink.gateway_id),
                )

    def do_gateways(self, line):
        """
        Displays the available gateways

        Usage:
            gateways

        Returns:
            Prints the discovered gateways
        """
        print("Printing all encountered gateways of MQTT broker")

        print(
            "gateway id".ljust(self._device_id_display_string_width),
            "( sink0 .. sinkN )",
        )
        sorted_device_list = self._sort_items_by_device_id(
            self.device_manager.gateways
        )
        for gateway in sorted_device_list:
            sink_list = gateway.sinks

            sinks_str: str
            sinks_str = ""
            sorted_sink_list = self._sort_items_by_device_id(sink_list)
            for sink in sorted_sink_list:
                sinks_str += "{} ".format(sink.device_id)

            sinks_str = sinks_str[:-1]

            if len(sinks_str) > 0:
                print(
                    str(gateway.gateway_id).ljust(
                        self._device_id_display_string_width
                    ),
                    "(",
                    sinks_str,
                    ")",
                )
            else:
                print(
                    str(gateway.gateway_id).ljust(
                        self._device_id_display_string_width
                    )
                )

    def do_nodes(self, line):
        """
        Displays the available nodes

        Usage:
            nodes

        Returns:
            Prints the discovered nodes
        """
        current_gateway = self._selection["gateway"]

        if current_gateway:
            print(
                "Printing all encountered nodes of gateway {}".format(
                    current_gateway.device_id
                )
            )
            filtered_nodes_list: list = list()
            filtered_nodes_list = self._filter_nodes_by_gateway_id(
                self.device_manager.nodes, current_gateway.device_id
            )

            nodes_str: str
            nodes_str = ""
            sorted_filtered_nodes = sorted(
                list(filtered_nodes_list), key=lambda item: int(item.device_id)
            )
            for node in sorted_filtered_nodes:
                nodes_str += "{} ".format(node.device_id)

            nodes_str = nodes_str[:-1]

            if len(nodes_str) > 0:
                nodes_str = "( {} )".format(nodes_str)
                print(nodes_str)

            print("Total {} nodes".format(len(list(filtered_nodes_list))))

        else:
            print("Printing all encountered nodes of MQTT broker")

            nodes_str: str
            nodes_str = ""

            sorted_filtered_nodes = sorted(
                list(self.device_manager.nodes),
                key=lambda item: int(item.device_id),
            )

            for node in sorted_filtered_nodes:
                nodes_str += "{} ".format(node.device_id)

            nodes_str = nodes_str[:-1]

            if len(nodes_str) > 0:
                nodes_str = "( {} )".format(nodes_str)
                print(nodes_str)
            print(
                "Total {} nodes".format(len(list(self.device_manager.nodes)))
            )

    def do_networks(self, line):
        """
        Displays the available networks

        Usage:
            networks

        Returns:
            Prints the discovered networks
        """

        print("Printing all encountered networks of MQTT")

        sorted_networks = sorted(
            list(self.device_manager.networks),
            key=lambda item: int(item.network_id),
        )

        for network in sorted_networks:
            print(network.network_id)

    def do_gateway_configuration(self, line):
        """
        Acquires gateway configuration from the server and updates
        self.device_manager

        If no gateway is set, it will acquire configuration from all
        online gateways.

        When a gateway is selected, the configuration will only be
        requested for that particular gateway.

        Usage:
            gateway_configuration

        Returns:
            Current configuration for each gateway
        """

        ret = list()

        for gateway in self.device_manager.gateways:

            if gateway.state.value == GatewayState.OFFLINE.value:
                continue

            if self.gateway is not None:
                if self.gateway.device_id != gateway.device_id:
                    continue

            gw_id = gateway.device_id

            print("requesting configuration for {}".format(gw_id))
            configurations = self._get_gateway_configuration(gateway.device_id)

            for config in configurations:
                if config is not None:
                    ret.append(config)

            # Todo check what return type is needed and return needed item.

    def _refresh_device_manager(self):
        # refresh device manager (gw, sinks) by requesting configurations from
        # gateways

        for gateway in self.device_manager.gateways:

            if gateway.state.value == GatewayState.OFFLINE.value:
                continue

            if self.gateway is not None:
                if self.gateway.device_id != gateway.device_id:
                    continue

            gw_id = gateway.device_id

            config = self._get_gateway_configuration(gateway.device_id)
            self.device_manager.update(gw_id, config)

    def do_set_app_config(self, line):
        """
        Builds and sends an app config message

        Usage:
            set_app_config  argument=value

        Arguments:
            - sequence=1  # the sequence number - must be higher than the current one
            - data=001100 # payloady in hex string or plain string
            - interval=60 # a valid diagnostic interval (by default 60)

        Returns:
            Result of the request and app config currently set
        """
        options = dict(
            app_config_seq=dict(type=int, default=None),
            app_config_data=dict(type=int, default=None),
            app_config_diag=dict(type=int, default=60),
        )

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            # sink_id interval app_config_data seq

            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            if not self.is_valid(args) or not sink_id:
                self.do_help("set_app_config", args)

            message = self.mqtt_topics.request_message(
                "set_config",
                **dict(
                    sink_id=sink_id,
                    gw_id=gateway_id,
                    new_config={
                        "app_config_diag": args["app_config_diag"],
                        "app_config_data": args["app_config_data"],
                        "app_config_seq": args["app_config_seq"],
                    },
                ),
            )

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id, message)

        else:
            self._set_target()
            self.do_set_app_config(line)

    def do_scratchpad_status(self, line):
        """
        Retrieves the scratchpad status from the sink

        Usage:
            scratchpad_status

        Returns:
            The scratchpad loaded on the target gateway:sink pair
        """

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_status", **dict(sink_id=sink_id, gw_id=gateway_id)
            )

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id, message)

        else:
            self._set_target()

    def do_scratchpad_update(self, line):
        """
        Sends a scratchpad update command to the sink

        Usage:
            scratchpad_update

        Returns:
            The update status
        """

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_process_scratchpad",
                **dict(sink_id=sink_id, gw_id=gateway_id),
            )

            message["qos"] = MQTT_QOS_options.exactly_once.value

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id, message)

        else:
            self._set_target()

    def do_scratchpad_upload(self, line):
        """
        Uploads a scratchpad to the target sink/gateway pair

        Usage:
            scratchpad_upload argument=value

        Arguments:
            - filepath=~/myscratchpad.otap # the path to the scratchpad
            - sequence=1 # the scratchpad sequence number

        Returns:
            The status of the upload success
        """

        options = dict(
            file_path=dict(type=int, default=None),
            seq=dict(type=int, default=None),
        )

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            try:
                with open(args["file_path"], "rb") as f:
                    scratchpad = f.read()
            except FileNotFoundError:
                scratchpad = None

            if not self.is_valid(args):
                self.do_help("scratchpad_upload", args)

            message = self.mqtt_topics.request_message(
                "otap_load_scratchpad",
                **dict(
                    sink_id=sink_id,
                    scratchpad=scratchpad,
                    seq=args["seq"],
                    gw_id=gateway_id,
                ),
            )
            message["qos"] = MQTT_QOS_options.exactly_once.value

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id, message)

        else:
            self._set_target()
            self.scratchpad_upload(line=line)

    def _build_default_mqtt_request_options(self):
        options = dict(
            source_endpoint=dict(type=int, default=None),
            destination_endpoint=dict(type=int, default=None),
            destination_address=dict(type=int, default=None),
            payload=dict(type=self.strtobytes, default=None),
            timeout=dict(type=int, default=0),
            qos=dict(type=int, default=MQTT_QOS_options.exactly_once.value),
            is_unack_csma_ca=dict(type=bool, default=0),
            hop_limit=dict(type=int, default=0),
            initial_delay_ms=dict(type=int, default=0),
        )
        return options

    def do_send_data(self, line):
        """
        Sends a custom payload to the target address.

        Usage:
            send_data argument=value

        Arguments:
            - source_endpoint= 10 (default=None)
            - destination_endpoint=11   (default=None)
            - destination_address=101   (default=None)
            - payload=0011   (default=None)
            - timeout=0 # skip wait for a response (default=0)
            - qos=MQTT_QOS_options.exactly_once
            - is_unack_csma_ca=0  # if true only sent to CB-MAC nodes (default=0)
            - hop_limit=0  # maximum number of hops this message can do to reach its destination (<16) (default=0 - disabled)
            - initial_delay_ms=0 # initial delay to add to travel time (default: 0)

        Returns:
            Answer or timeout
        """

        options = self._build_default_mqtt_request_options()

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:

            if not self.is_valid(args):
                self.do_help("send_data", args)
            else:
                gateway_id = self.gateway.device_id
                sink_id = self.sink.device_id

                message = self.mqtt_topics.request_message(
                    "send_data",
                    **dict(
                        sink_id=sink_id,
                        dest_add=args["destination_address"],
                        src_ep=args["source_endpoint"],
                        dst_ep=args["destination_endpoint"],
                        payload=args["payload"],
                        qos=args["qos"],
                        is_unack_csma_ca=args["is_unack_csma_ca"],
                        hop_limit=args["hop_limit"],
                        initial_delay_ms=args["initial_delay_ms"],
                        gw_id=gateway_id,
                    ),
                )

                print(message["data"])
                return

                message["qos"] = MQTT_QOS_options.exactly_once.value
                self.request_queue.put(message)
                self.wait_for_answer(gateway_id, message)
        else:
            self._set_target()
            self.do_send_data(line)

    def send_message_to_mqtt_async(
        self,
        gatewayId,
        sinkId,
        nodeDestinationAddress,
        destinationEndPoint,
        sourceEndPoint,
        payload,
    ):

        # options = self._build_default_mqtt_request_options()

        message = self.mqtt_topics.request_message(
            "send_data",
            **dict(
                sink_id=sinkId,
                dest_add=nodeDestinationAddress,
                src_ep=sourceEndPoint,
                dst_ep=destinationEndPoint,
                payload=payload,
                qos=MQTT_QOS_options.exactly_once.value,
                is_unack_csma_ca=0,
                hop_limit=0,
                initial_delay_ms=0,
                gw_id=gatewayId,
            ),
        )

        message["qos"] = MQTT_QOS_options.exactly_once.value
        requestIdOfMessageToBeSent = message["data"].req_id

        dummyMode: bool = False  # If True, no messages is actually sent

        if dummyMode is True:
            print("Skipping sending ")
        else:
            self.request_queue.put(message)
        return requestIdOfMessageToBeSent

    def do_set_config(self, line):
        """
        Set a config on the target sink.

        Usage:
            set_config argument=value

        Arguments:
            - node_role=1 (int),
            - node_address=1003 (int),
            - network_address=100 (int),
            - network_channel=1 (int)
            - started=True (bool)

        Returns:
            Answer or timeout
        """
        options = dict(
            node_role=dict(type=int, default=None),
            node_address=dict(type=int, default=None),
            network_address=dict(type=int, default=None),
            network_channel=dict(type=int, default=None),
            started=dict(type=bool, default=None),
        )
        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            new_config = {}
            for key, val in args:
                if val:
                    new_config[key] = val

            if not new_config:
                self.do_help("set_config", args)

            message = self.mqtt_topics.request_message(
                "set_config",
                **dict(
                    sink_id=sink_id, gw_id=gateway_id, new_config=new_config
                ),
            )
            self.request_queue.put(message)
            self.wait_for_answer(
                f"{gateway_id}/{sink_id}", message, timeout=self.timeout
            )

        else:
            self._set_target()

    def _getMenuOption(self, menuText: str, options: list):

        minValue = 0
        maxValue = len(options) - 1

        print(" ")
        print(menuText)

        menuId = 0
        for option in options:
            print("{}: {}".format(menuId, option))
            menuId += 1

        # print(menuText)
        inputStr = ""
        while (
            self._validateNumericInput(inputStr, minValue, maxValue) is False
        ):
            inputStr = input("[{}-{}]: ".format(minValue, maxValue)) or 0
        ret = options[int(inputStr)]
        return ret

    def _validateNumericInput(
        self, inputStr: str, minValue: int, maxValue: int
    ):
        ret: bool = False
        if inputStr.isnumeric():
            inputValue = int(inputStr)
            if minValue <= inputValue <= maxValue:
                ret = True

        return ret

    def _filter_online_gateways(self, gateways):
        online_gw_list: list = list()

        for gw in gateways:
            if str(gw.state) == "GatewayState.ONLINE":
                online_gw_list.append(gw)
        return online_gw_list

    def do_set_ndiag(self, line):
        """
        Enables or disables neighbor diagnostics on network level

        Usage:
            set_ndiag

            Application will ask parameters after invocation of command.

        Arguments asked from user:
            - Network ID
            - Diagnostic interval or off
            - Configuration for performing operation or cancel

        Returns:
            Prints progress on screen.
            There is a timeout.
        """

        print("Set neighbor diagnostics for network")
        print("")

        print("Refresh network list..")
        self._refresh_device_manager()
        sorted_networks = sorted(
            list(self.device_manager.networks),
            key=lambda item: int(item.network_id),
        )

        networkList: list
        networkList = list()
        for nw in sorted_networks:
            networkList.append(nw.network_id)

        if len(networkList) > 0:
            selectionID: int
            argNetworkId = self._getMenuOption(
                "Please enter network to be operated", networkList
            )

            argDiagnosticIntervalSec: SetDiagnosticsIntervals
            offOption = "off"
            diagnosticIntervalSelection = self._getMenuOption(
                "Select diagnostic interval(s) or off option",
                [
                    offOption,
                    SetDiagnosticsIntervals.i30.value,
                    SetDiagnosticsIntervals.i60.value,
                    SetDiagnosticsIntervals.i120.value,
                    SetDiagnosticsIntervals.i300.value,
                    SetDiagnosticsIntervals.i1200.value,
                ],
            )

            if diagnosticIntervalSelection == offOption:
                argDiagnosticIntervalSec = (
                    SetDiagnosticsIntervals.intervalOff.value
                )
            else:
                argDiagnosticIntervalSec = diagnosticIntervalSelection

            featureObject = SetDiagnostics(self.device_manager)

            if (
                featureObject.setArguments(
                    int(argNetworkId), argDiagnosticIntervalSec
                )
                is True
            ):

                targetSinks = featureObject.getSinksBelongingToNetwork(
                    int(argNetworkId)
                )

                sinksAddressInfo = dict()

                sinkAddressCheckOk: bool = True
                sinkAddressCheckOk = self.createSinkAddressInfo(
                    sinkAddressCheckOk, sinksAddressInfo, targetSinks
                )

                if sinkAddressCheckOk is True:
                    print(" ")
                    print("About to send messages to:")
                    targetList = ""
                    for gw in targetSinks:
                        for sink in targetSinks[gw]:
                            targetList += "{}/{}:{}  ".format(
                                gw, sink, sinksAddressInfo[gw][sink]
                            )
                    print(targetList)

                    uiCommandOptionProceedYes = "yes"
                    uiCommandOptionoptionProceedNo = "no"

                    proceed = self._getMenuOption(
                        "Args good. Proceed?",
                        [
                            uiCommandOptionoptionProceedNo,
                            uiCommandOptionProceedYes,
                        ],
                    )

                    if proceed == uiCommandOptionProceedYes:
                        featureObject.setMQTTmessageSendFunction(
                            self.send_message_to_mqtt_async
                        )

                        featureObject.setSinksAddressInfo(sinksAddressInfo)

                        self.set_message_handlers(
                            featureObject.onDataQueueMessage,
                            featureObject.onEventQueueMessage,
                            featureObject.onResponseQueueMessage,
                        )

                        exitWorkers = False

                        def applicationLoopWorker():
                            featureObject.performOperation()
                            nonlocal exitWorkers
                            exitWorkers = True

                        def backEndClientMessageLoopWorker():
                            # Todo Move this to upper level.
                            # Now here because not knowing the
                            # impacts yet.
                            nonlocal exitWorkers
                            while exitWorkers is False:
                                msgReceived = False
                                msg = self.get_message_from_response_queue()
                                if msg is not None:
                                    msgReceived = True
                                    self.on_response_queue_message(msg)

                                msg = self.get_message_from_data_queue()
                                if msg is not None:
                                    msgReceived = True
                                    self.on_data_queue_message(msg)

                                msg = self.get_message_from_event_queue()
                                if msg is not None:
                                    msgReceived = True
                                    self.on_event_queue_message(msg)

                                if msgReceived is False:
                                    defaultSleepSecs = 0.05
                                    sleep(defaultSleepSecs)

                        t1 = threading.Thread(target=applicationLoopWorker)
                        t2 = threading.Thread(
                            target=backEndClientMessageLoopWorker
                        )
                        t1.start()
                        t2.start()

                        # Work start tha this remains blocked until threads
                        # complete

                        t1.join()
                        t2.join()
                        self._clear_message_handlers()
                    else:
                        print(" ")
                        print("Aborted!")
                else:
                    print(" ")
                    print("Sink node address lookup failed!")
            else:
                print(" ")
                print("Arguments not valid!")
        else:
            print(" ")
            print("No networks available!")

    def createSinkAddressInfo(
        self, sinkAddressCheckOk, sinksAddressInfo, targetSinks
    ):
        for gw in targetSinks:
            for sink in targetSinks[gw]:
                sinkNodeAddress = self._lookup_node_address(gw, sink)
                if sinkNodeAddress is not None:
                    if gw not in sinksAddressInfo:
                        sinksAddressInfo[gw] = dict()

                    if sink not in sinksAddressInfo[gw]:
                        sinksAddressInfo[gw][sink] = dict()

                    sinksAddressInfo[gw][sink] = sinkNodeAddress
                else:
                    sinkAddressCheckOk = False
                    break
        return sinkAddressCheckOk
