"""
    Backend
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import datetime
import logging
import queue

from .manager import AuthenticationManager, RealtimeManager, MetadataManager
from wirepas_backend_client.tools import JsonSerializer


class Backend(object):
    """
        Backend

        The Backend class aims to support a connection to a given WNT
        instance. It assumes default ports for the client websockets.

    """

    def __init__(
        self, settings, callback_queue=None, logger=None, **kwargs
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.settings = settings
        self.session_id = None
        self.serializer = JsonSerializer()

        self.authentication = AuthenticationManager(
            hostname=self.settings.wnt_hostname,
            username=self.settings.wnt_username,
            password=self.settings.wnt_password,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

        self.realtime = RealtimeManager(
            hostname=self.settings.wnt_hostname,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

        self.metadata = MetadataManager(
            hostname=self.settings.wnt_hostname,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

    def login(self) -> None:
        """
        login retrieves a session id from the authentication ws.

        If the acquisition is successful, the token is stored under
        the objects's session_id attribute.

        """

        self.authentication.start()
        message = self.authentication.tx_queue.get(block=True)

        try:
            self.session_id = message["session_id"]
        except KeyError:
            self.logger.exception("Failed to find session id")
            raise

        self.realtime.rx_queue.put(dict(session_id=self.session_id))
        self.metadata.rx_queue.put(dict(session_id=self.session_id))

    def send_request(self) -> None:
        """
        Send request

        Placeholder to handle sending requests through the websocket
        interface.
        """

    def tasks(self, exit_signal: bool) -> None:
        """
        tasks defines the run loop's procedures.

        Please overload this method if you wish to customize the workflow
        against a Backend.
        """

        while not exit_signal:
            try:
                message = self.realtime.tx_queue.get(block=True, timeout=10)
                if message:
                    self.logger.info(
                        "%s | %s",
                        datetime.datetime.utcnow().isoformat("T"),
                        self.serializer.serialize(message),
                    )
            except queue.Empty:
                pass

    def close(self):
        """ Terminates the websocket connections """
        self.metadata.stop()
        self.realtime.stop()
        self.authentication.stop()

    def run(self, exit_signal: bool) -> None:
        """ Defines the object's main loop """
        self.login()
        self.metadata.start()
        self.realtime.start()
        self.tasks(exit_signal)
        self.close()


if __name__ == "__main__":

    print("Please use the package's entrypoint.")
