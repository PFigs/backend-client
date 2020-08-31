"""
    Stream API
    ============

    Contains a generic class to handle IO streams.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import logging
import multiprocessing


class StreamObserver(object):
    """
    StreamObserver

    Simple interface class to store and manage the queue access

    Attributes:
        push_data: signal to start sending data to the tx_queue
        tx_queue: where to PUT packets
        rx_queue: where to GET packets
        logger: logging interface

    """

    # pylint: disable=locally-disabled, too-many-arguments,

    def __init__(
        self,
        start_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        exit_signal: multiprocessing.Event = None,
        logger: logging.Logger = None,
    ) -> "StreamObserver":
        super(StreamObserver, self).__init__()

        self.start_signal = start_signal
        self.exit_signal = exit_signal
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.logger = logger

    def send_data(self, timeout: int, block: bool):
        """ puts data on the outbound queue """
        raise NotImplementedError

    def receive_data(self, timeout: int, block: bool):
        """ retrieves data from the inbound queue """
        raise NotImplementedError

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """
        return self.receive_data

    def generate_data_send_cb(self) -> callable:
        """ Returns a callback to publish the outgoing data """
        return self.send_data
