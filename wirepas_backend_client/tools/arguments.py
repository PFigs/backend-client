"""
    Arguments
    =========

    Contains helpers to parse application arguments

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import argparse
import os
import ssl
import sys

import yaml

from wirepas_backend_client.tools.utils import JsonSerializer
from wirepas_backend_client.__about__ import __version__


class Settings:
    """Simple class to handle library settings"""

    _MANDATORY_FIELDS = list()

    def __init__(self, settings: dict):
        super(Settings, self).__init__()

        self.debug_level = None

        for k, v in settings.items():
            self.__dict__[k] = v

    def items(self):
        """ returns the internal dictionary items """
        return self.__dict__.items()

    def sanity(self) -> bool:
        """
        Validity serves as a mean to check if the settings are valid.
        For example, for database settings it should ensure that the
        hostname, username and password are at least not None.

        By default, it assumes all settings are valid.
        """

        is_valid = True
        for field in self._MANDATORY_FIELDS:
            if getattr(self, field) is None:
                is_valid = False
                break
        return is_valid

    def to_dict(self):
        """ Returns the objects internal dictionary """
        return self.__dict__

    def _helper_str(self, key_filter=None) -> str:
        mystr = ""
        for key, value in self.__dict__.items():
            if "password" in "key":
                if value is not None:
                    value = "password_is_set"
            if key_filter is not None:
                if key_filter not in key:
                    continue
            hint = "optional"
            if key in self._MANDATORY_FIELDS:
                hint = "required"

            mystr += "{}: {} ({})\n".format(key, value, hint)
        return mystr

    def __str__(self) -> str:
        return self._helper_str(key_filter=None)


class ParserHelper:
    """
    ParserHelper

    Handles the creation and decoding of arguments
    """

    _short_options = list()

    def __init__(
        self,
        description="argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ):
        super(ParserHelper, self).__init__()
        self._parser = argparse.ArgumentParser(
            description=description, formatter_class=formatter_class
        )

        self._unknown_arguments = None
        self._arguments = None
        self._groups = dict()
        self._version = __version__

        self.add_framework_settings()

    @property
    def parser(self):
        """ Returns the parser object """
        return self._parser

    @property
    def arguments(self):
        """
        Returns arguments that it can parse and throwing an error
        otherwise
        """
        return self._arguments

    @property
    def known_arguments(self):
        """ returns the unknown arguments it could not parse """
        (
            self._arguments,
            self._unknown_arguments,
        ) = self.parser.parse_known_args()
        return self._arguments

    @property
    def unkown_arguments(self):
        """ returns the unknown arguments it could not parse """
        return self._unknown_arguments

    def settings(self, settings_class=None):
        """ Reads an yaml settings file and puts it through argparse """

        # Parse args from cmd line to see if a custom setting file is specified
        self._arguments = self.parser.parse_args()

        if self._arguments.settings is not None:
            try:
                with open(self._arguments.settings, "r") as f:
                    settings = yaml.load(f, Loader=yaml.FullLoader)
                    arglist = list()

                    # Add the file parameters
                    for key, value in settings.items():
                        if key in self._short_options:
                            key = "-{}".format(key)
                        else:
                            key = "--{}".format(key)

                        # We assume that booleans are always handled with
                        # store_true. This logic will fail otherwise.
                        if value is False:
                            continue

                        arglist.append(key)

                        # do not append True as the key is enough
                        if value is True:
                            continue
                        arglist.append(str(value))

                    arguments = sys.argv
                    argument_index = 1  # wm-gw
                    if "python" in arguments[0]:  # pythonX transport (...)
                        if "-m" in arguments[1]:  # pythonX -m transport (...)
                            argument_index += 1
                        argument_index = +1
                    # Add the cmd line parameters. They will override
                    # parameters from file if set in both places.
                    for arg in arguments[argument_index:]:
                        arglist.append(arg)

                # Override self._arguments as there are parameters from file
                (
                    self._arguments,
                    self._unknown_arguments,
                ) = self.parser.parse_known_args(arglist)
            except FileNotFoundError:
                pass

        if settings_class is None:
            settings_class = Settings

        settings = settings_class(self._arguments.__dict__)

        return settings

    def __getattr__(self, name):
        if name not in self._groups:
            self._groups[name] = self._parser.add_argument_group(name)

        return self._groups[name]

    def add_framework_settings(self):
        """ Adds arguments regarding the backend client operation """
        self.framework.add_argument(
            "--version", action="version", version=self._version
        )

        self.framework.add_argument(
            "--debug_level",
            action="store",
            default=os.environ.get("WM_DEBUG_LEVEL", None),
            type=str,
            help="Logger debug level",
        )

        self.framework.add_argument(
            "--heartbeat",
            action="store",
            default=os.environ.get("WM_BCLI_HEARTBEAT", 10),
            type=int,
            help="Amount of seconds to check if processes are alive",
        )

    def add_file_settings(self):
        """ For file setting handling"""
        self.file_settings.add_argument(
            "--settings",
            type=str,
            required=False,
            default=os.environ.get("WM_BCLI_FILE_SETTINGS", None),
            help="settings file.",
        )

    def add_mqtt(self):
        """ Commonly used MQTT arguments """

        self.mqtt.add_argument(
            "--mqtt_hostname",
            default=os.environ.get("WM_SERVICES_MQTT_HOSTNAME", None),
            action="store",
            type=str,
            help="MQTT broker hostname ",
        )

        self.mqtt.add_argument(
            "--mqtt_username",
            default=os.environ.get("WM_SERVICES_MQTT_USERNAME", None),
            action="store",
            type=str,
            help="MQTT broker username ",
        )

        self.mqtt.add_argument(
            "--mqtt_password",
            default=os.environ.get("WM_SERVICES_MQTT_PASSWORD", None),
            action="store",
            type=str,
            help="MQTT broker password",
        )

        self.mqtt.add_argument(
            "--mqtt_port",
            default=os.environ.get("WM_SERVICES_MQTT_PORT", 8883),
            action="store",
            type=int,
            help="MQTT broker port",
        )

        self.mqtt.add_argument(
            "--mqtt_ca_certs",
            default=os.environ.get("WM_SERVICES_MQTT_CA_CERTS", None),
            action="store",
            type=str,
            help=(
                "A string path to the Certificate "
                "Authority certificate files that "
                "are to be treated as trusted by "
                "this client"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_certfile",
            default=os.environ.get("WM_SERVICES_MQTT_CLIENT_CRT", None),
            action="store",
            type=str,
            help=("Strings pointing to the PEM encoded client certificate"),
        )

        self.mqtt.add_argument(
            "--mqtt_keyfile",
            default=os.environ.get("WM_SERVICES_MQTT_CLIENT_KEY", None),
            action="store",
            type=str,
            help=(
                "Strings pointing to the PEM "
                "encoded client private keys "
                "respectively"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_cert_reqs",
            default=os.environ.get(
                "WM_SERVICES_MQTT_CERT_REQS", ssl.CERT_REQUIRED
            ),
            action="store",
            type=str,
            help=(
                "Defines the certificate "
                "requirements that the client "
                "imposes on the broker"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_tls_version",
            default=os.environ.get(
                "WM_SERVICES_MQTT_TLS_VERSION", ssl.PROTOCOL_TLSv1_2
            ),
            action="store",
            type=str,
            help=(
                "Specifies the version of the  SSL / TLS protocol to be used"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_ciphers",
            default=os.environ.get("WM_SERVICES_MQTT_CIPHERS", None),
            action="store",
            type=str,
            help=(
                "A string specifying which "
                "encryption ciphers are allowable "
                "for this connection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_persist_session",
            default=os.environ.get("WM_SERVICES_MQTT_PERSIST_SESSION", False),
            action="store_true",
            help=(
                "When False the broker will buffer"
                "session packets between "
                "reconnection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_force_unsecure",
            default=os.environ.get("WM_SERVICES_MQTT_FORCE_UNSECURE", False),
            action="store_true",
            help=("When True the broker will skip the TLS handshake"),
        )

        self.mqtt.add_argument(
            "--mqtt_allow_untrusted",
            default=os.environ.get("WM_SERVICES_MQTT_ALLOW_UNTRUSTED", False),
            action="store_true",
            help=(
                "When true the client will skip the certificate name check."
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_topic",
            default=os.environ.get("WM_SERVICES_MQTT_SUB_TOPIC", "#"),
            action="store",
            type=str,
            help="MQTT topic to subscribe to",
        )

        self.mqtt.add_argument(
            "--mqtt_subscribe_network_id",
            default=os.environ.get("WM_SERVICES_MQTT_SUB_NETWORK_ID", "+"),
            action="store",
            type=str,
            help=(
                "Specifies the WM sink id to use in the gateway topic subscription"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_subscribe_sink_id",
            default=os.environ.get("WM_SERVICES_MQTT_SUB_SINK_ID", "+"),
            action="store",
            type=str,
            help=(
                "Specifies the WM sink id to use in the gateway topic subscription"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_subscribe_gateway_id",
            default=os.environ.get("WM_SERVICES_MQTT_SUB_GATEWAY_ID", "+"),
            action="store",
            type=str,
            help=(
                "Specifies the WM gateway id to use in the gateway topic subscription"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_subscribe_source_endpoint",
            default=os.environ.get(
                "WM_SERVICES_MQTT_SUB_SOURCE_ENDPOINT", "+"
            ),
            action="store",
            type=str,
            help=(
                "Specifies the WM source endpoint to use in the gateway topic subscription"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_subscribe_destination_endpoint",
            default=os.environ.get(
                "WM_SERVICES_MQTT_SUB_DESTINATION_ENDPOINT", "+"
            ),
            action="store",
            type=str,
            help=(
                "Specifies the WM destination endpoint to use in the gateway topic subscription"
            ),
        )

    def add_test(self):
        """ Commonly used arguments for test execution """
        self.test.add_argument(
            "--testcase",
            default=os.environ.get("WM_BCLI_TEST_TEST_CASE", None),
            type=str,
            choices={"inventory", "reliability"},
            help="The test case name, the choice is 'inventory' or 'reliability'",
        )
        self.test.add_argument(
            "--delay",
            default=os.environ.get("WM_BCLI_TEST_DELAY", None),
            type=int,
            help="Initial wait in seconds - set None for random",
        )

        self.test.add_argument(
            "--duration",
            default=os.environ.get("WM_BCLI_TEST_DURATION", 10),
            type=int,
            help="Time to collect data for",
        )

        self.test.add_argument(
            "--reliability_message_window",
            default=os.environ.get("WM_BCLI_TEST_MESSAGE_WINDOW", 20),
            type=int,
            help="the message window used when checking the missed packet",
        )

        self.test.add_argument(
            "--reliability_raw_data",
            default=os.environ.get("WM_BCLI_TEST_RAW_DATA", False),
            action="store_true",
            help="whether the reliability raw data will be save",
        )

        self.test.add_argument(
            "--nodes",
            default=os.environ.get("WM_BCLI_TEST_NODES", "./nodes.txt"),
            type=str,
            help="File with list of nodes to observe",
        )

        self.test.add_argument(
            "--jitter_minimum",
            default=os.environ.get("WM_BCLI_TEST_JITTER_MIN", 0),
            type=int,
            help="Minimum amount of sleep between tasks",
        )

        self.test.add_argument(
            "--jitter_maximum",
            default=os.environ.get("WM_BCLI_TEST_JITTER_MAX", 0),
            type=int,
            help="Maximum amount of sleep between tasks",
        )

        self.test.add_argument(
            "--input",
            default=os.environ.get("WM_BCLI_TEST_INPUT", None),
            type=str,
            help="file where to read from",
        )

        self.test.add_argument(
            "--output",
            default=os.environ.get("WM_BCLI_TEST_OUTPUT", None),
            type=str,
            help="file where to ouput the report",
        )

        self.test.add_argument(
            "--output_time",
            default=os.environ.get("WM_BCLI_TEST_OUTPUT_TIME", False),
            action="store_true",
            help=("appends datetime information to the output filename"),
        )

        self.test.add_argument(
            "--target_otap",
            default=os.environ.get("WM_BCLI_TEST_TARGET_OTAP", None),
            type=int,
            help="target_otap",
        )

        self.test.add_argument(
            "--target_frequency",
            default=os.environ.get("WM_BCLI_TEST_TARGET_FREQUENCY", None),
            type=int,
            help=("Number of messages that should be observed for each node"),
        )

        self.test.add_argument(
            "--number_of_runs",
            default=os.environ.get("WM_BCLI_TEST_NUMBER_RUNS", 1),
            type=int,
            help="Number of test runs to execute",
        )

    def add_fluentd(self):
        """ Commonly used fluentd arguments """
        self.fluentd.add_argument(
            "--fluentd_hostname",
            default=os.environ.get("WM_SERVICES_FLUENTD_HOSTNAME", None),
            action="store",
            type=str,
            help="Fluentd hostname",
        )

        self.fluentd.add_argument(
            "--fluentd_port",
            default=os.environ.get("WM_SERVICES_FLUENTD_PORT", 24224),
            action="store",
            type=int,
            help="Fluentd port",
        )

        self.fluentd.add_argument(
            "--fluentd_record",
            default=os.environ.get("WM_SERVICES_FLUENTD_RECORD", "log"),
            action="store",
            type=str,
            help="Name of record to use (tag.record)",
        )

        self.fluentd.add_argument(
            "--fluentd_tag",
            default=os.environ.get("WM_SERVICES_FLUENTD_TAG", "python"),
            action="store",
            type=str,
            help="How to tag outgoing data to fluentd",
        )

    def add_wnt(self):
        """ WNT related settings """

        self.wnt.add_argument(
            "--wnt_hostname",
            default=os.environ.get("WM_SERVICES_WNT_HOSTNAME", None),
            type=str,
            help="domain where to point requests.",
        )

        self.wnt.add_argument(
            "--wnt_username",
            type=str,
            required=False,
            default=os.environ.get("WM_SERVICES_WNT_USERNAME", None),
            help="username to login with.",
        )

        self.wnt.add_argument(
            "--wnt_password",
            type=str,
            default=os.environ.get("WM_SERVICES_WNT_PASSWORD", None),
            help="password for user.",
        )

        self.wnt.add_argument(
            "--wnt_protocol_version",
            type=int,
            default=os.environ.get("WM_SERVICES_WNT_WS_PROTOCOL", 2),
            help="WS API protocol version.",
        )

    def add_wpe(self):
        """ Commonly used http server arguments """
        self.wpe.add_argument(
            "--wpe_service_definition",
            type=str,
            required=False,
            default=os.environ.get(
                "WM_SERVICES_WPE_SERVICE_DEFINITION", "./services.json"
            ),
            help="service configuration file.",
        )

        self.wpe.add_argument(
            "--wpe_unsecure",
            required=False,
            default=os.environ.get("WM_SERVICES_WPE_UNSECURE", False),
            action="store_true",
            help="forces the creation of insecure channels.",
        )

        self.wpe.add_argument(
            "--wpe_network",
            required=False,
            default=os.environ.get("WM_SERVICES_WPE_NETWORK", None),
            type=int,
            help="network id to subscribe to.",
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        serializer = JsonSerializer()
        with open(path, "w") as f:
            f.write(serializer.serialize(vars(self._arguments)))
