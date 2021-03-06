"""
    Handlers
    =========

    Contains class to handle MySQL interaction

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import os

try:
    import MySQLdb
except ImportError:
    pass

import logging
import multiprocessing
import queue
import time

from ..stream import StreamObserver
from ...messages import AdvertiserMessage
from ...messages import BootDiagnosticsMessage
from ...messages import NeighborDiagnosticsMessage
from ...messages import NodeDiagnosticsMessage
from ...messages import TestNWMessage
from ...messages import TrafficDiagnosticsMessage
from ...messages import DiagnosticsMessage
from ...tools import Settings


from .connectors import MySQL


class MySQLObserver(StreamObserver):
    """ MySQLObserver monitors the internal queues and dumps events to the database """

    def __init__(
        self,
        mysql_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        parallel: bool = True,
        n_workers: int = 10,
        timeout: int = 10,
        logger=None,
    ) -> "MySQLObserver":
        super(MySQLObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.mysql = MySQL(
            username=mysql_settings.username,
            password=mysql_settings.password,
            hostname=mysql_settings.hostname,
            port=mysql_settings.port,
            database=mysql_settings.database,
            connection_timeout=mysql_settings.connection_timeout,
            logger=self.logger,
        )
        self.settings = mysql_settings
        self.timeout = timeout
        self.parallel = parallel
        self.n_workers = n_workers

    def on_data_received(self):
        """ Monitor inbound queue for messages to be stored in MySQL """

        while not self.exit_signal.is_set():

            try:
                message = self.rx_queue.get(timeout=self.timeout, block=True)
            except queue.Empty:
                message = None
                continue

            self._map_message(self.mysql, message)

    @staticmethod
    def _map_message(mysql, message):
        """ Inserts the message according to its type """
        mysql.put_to_received_packets(message)
        if isinstance(message, DiagnosticsMessage):
            mysql.put_diagnostics(message)
        elif isinstance(message, AdvertiserMessage):
            mysql.put_advertiser(message)
        elif isinstance(message, TestNWMessage):
            mysql.put_testnw_measurements(message)
        elif isinstance(message, BootDiagnosticsMessage):
            mysql.put_boot_diagnostics(message)
        elif isinstance(message, NeighborDiagnosticsMessage):
            mysql.put_neighbor_diagnostics(message)
        elif isinstance(message, NodeDiagnosticsMessage):
            mysql.put_node_diagnostics(message)
        elif isinstance(message, TrafficDiagnosticsMessage):
            mysql.put_traffic_diagnostics(message)

    def pool_on_data_received(self, n_workers=10):
        """ Monitor inbound queue for messages to be stored in MySQL """

        def work(storage_q, exit_signal, settings, timeout, logger):

            mysql = MySQL(
                username=settings.username,
                password=settings.password,
                hostname=settings.hostname,
                port=settings.port,
                database=settings.database,
                connection_timeout=settings.connection_timeout,
                logger=logger,
            )

            mysql.connect(table_creation=False)
            pid = os.getpid()

            logger.info("starting MySQL worker %s", pid)

            while not exit_signal.is_set():
                try:
                    message = storage_q.get(block=True, timeout=timeout)
                except queue.Empty:
                    continue
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break

                try:
                    mysql.database.ping(True)
                except MySQLdb.OperationalError:
                    logger.exception(
                        "MySQL worker %s: connection restart failed.", pid
                    )
                    mysql.close()
                    while not exit_signal.is_set():
                        try:
                            mysql.connect(table_creation=False)
                            logger.exception(
                                "MySQL worker %s: connection restart failed.",
                                pid,
                            )
                            break
                        except MySQLdb.Error:
                            logger.exception(
                                "MySQL worker %s: connection restart failed.",
                                pid,
                            )
                            time.sleep(5)

                if not exit_signal.is_set():
                    try:
                        MySQLObserver._map_message(mysql, message)
                    except MySQLdb.Error:
                        logger.exception(
                            "MySQL worker %s: connection restart failed.", pid
                        )

            logger.warning("exiting MySQL worker %s", pid)
            return pid

        workers = dict()
        for pseq in range(1, n_workers):
            workers[pseq] = multiprocessing.Process(
                target=work,
                args=(
                    self.rx_queue,
                    self.exit_signal,
                    self.settings,
                    self.timeout,
                    self.logger,
                ),
            ).start()

        self._wait_for_exit(workers=workers)

    def run(self, **kwargs):
        """ Runs until asked to exit """
        try:
            self.parallel = kwargs["parallel"]
        except KeyError:
            pass

        try:
            self.n_workers = kwargs["n_workers"]
        except KeyError:
            pass

        try:
            self.mysql.connect()
        except Exception as err:
            self.logger.exception("error connecting to database %s", err)
            self.exit_signal.set()
            raise

        if self.parallel:
            self.logger.info(
                "Starting // mysql work. " "Number of workers is %s",
                self.n_workers,
            )
            self.pool_on_data_received(n_workers=self.n_workers)
        else:
            self.logger.info("Starting single threaded mysql work")
            self.on_data_received()

        self.mysql.close()

    def _wait_for_exit(self, workers: dict = None):
        """ waits until the exit signal is set """
        while not self.exit_signal.is_set():
            self.logger.debug(
                "MySQL is running (waiting for %s)", self.timeout
            )
            time.sleep(self.timeout)
            if workers:
                for seq, worker in workers.items():
                    if worker.is_alive():
                        continue
                    self.logger.error("Worker %s is dead. Exiting", seq)
                    self.exit_signal.set()
                    break
