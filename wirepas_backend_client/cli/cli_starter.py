"""
    CLI gateway client
    ==================

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""


from .shell import GatewayShell

from wirepas_backend_client.management import Daemon
from wirepas_backend_client.mesh.interfaces.mqtt import NetworkDiscovery
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.api.mqtt import MQTTSettings


def launch_gw_cli(settings, logger):
    """ command line launcher """

    # process management
    daemon = Daemon(logger=logger)

    shared_state = daemon.create_shared_dict(devices=None)
    data_queue = daemon.create_queue()
    event_queue = daemon.create_queue()

    discovery = daemon.build(
        "discovery",
        NetworkDiscovery,
        dict(
            shared_state=shared_state,
            data_queue=data_queue,
            event_queue=event_queue,
            mqtt_settings=settings,
            logger=logger,
        ),
    )

    shell = GatewayShell(
        shared_state=shared_state,
        data_queue=data_queue,
        event_queue=event_queue,
        rx_queue=discovery.tx_queue,
        tx_queue=discovery.rx_queue,
        settings=settings,
        exit_signal=daemon.exit_signal,
        logger=logger,
    )
    daemon.set_loop(shell.cmdloop)
    daemon.start()


def start_cli():
    """ entrypoint loop """

    parser = ParserHelper("Gateway client arguments")
    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_fluentd()
    settings = parser.settings(settings_class=MQTTSettings)

    if settings.debug_level is None:
        settings.debug_level = "warning"

    logger = LoggerHelper(
        module_name="gw-cli", args=settings, level=settings.debug_level
    ).setup()

    if settings.sanity():
        launch_gw_cli(settings, logger)
    else:
        print("Please review your connection settings")
        print(settings)
