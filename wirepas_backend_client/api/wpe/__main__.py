"""
    WPE Client
    ==========

    Simple example on how to communicate with the
    wirepas positioning services

    For this example to run successfully,
    you will need to have an instance
    of the engine up and running.

    You will also need a valid service
    definition file with the correct
    certificates in place

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import datetime
import json

import wirepas_messaging.wpe as messaging

from .connectors import Service
from .settings import WPESettings
from wirepas_backend_client.tools import (
    ParserHelper,
    LoggerHelper,
    JsonSerializer,
)


def main():
    """ Main entrypoint to connect and talk to a WPE instance """

    PARSE = ParserHelper(description="WPE client arguments")

    PARSE.add_file_settings()
    PARSE.add_fluentd()
    PARSE.add_wpe()

    SETTINGS = PARSE.settings(settings_class=WPESettings)

    LOGGER = LoggerHelper(
        module_name="wm-wpe-viewer", args=SETTINGS, level=SETTINGS.debug_level
    ).setup()

    if SETTINGS.sanity():

        # loads connection details from a json file
        service_definition = json.loads(
            open(SETTINGS.wpe_service_definition).read()
        )
        service = Service(
            service_definition["flow"],
            service_handler=messaging.flow_managerStub,
        )
        service.dial(unsecure=SETTINGS.wpe_unsecure)

        # checks if the remote server is connected
        try:
            response = service.stub.status(messaging.Query())
            LOGGER.debug("%s", response)

        except Exception as err:
            LOGGER.exception("failed to query status - %s", err)

        # subscribe to the flow if a network id is provided
        if SETTINGS.wpe_network is not None:
            subscription = messaging.Query(network=SETTINGS.wpe_network)
            status = service.stub.subscribe(subscription)
            LOGGER.debug("subscription status: %s", status)

            if status.code == status.CODE.Value("SUCCESS"):
                serializer = JsonSerializer()
                subscription.subscriber_id = status.subscriber_id
                LOGGER.info("observation starting for: %s", subscription)

                try:
                    for message in service.stub.observe(subscription):
                        LOGGER.info(
                            "%s | %s",
                            datetime.datetime.utcnow().isoformat("T"),
                            serializer.serialize(message),
                        )

                except KeyboardInterrupt:
                    pass

                subscription = service.stub.unsubscribe(subscription)
                LOGGER.info("subscription termination: %s", subscription)

            else:
                LOGGER.error("insufficient parameters")

    else:
        print("Please provide a valid service definition file")
        print(SETTINGS)


if __name__ == "__main__":

    main()
