"""
    Daemon
    ======

    Contains a generic class to manange processes

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import logging
import multiprocessing
import time

queue_max_size: int = 100000


class Daemon(object):
    """
    Daemon

    Creates an abstraction around the process and queue management

    Attributes:
        heartbeat (int): amount of time to sleep between process status check
        join_timeout (int): amount of time wait for a process to join
        loop_cb (int): function to run while waiting for exit signal
        loop_kwargs (int): dictionary with loop function arguments

    """

    def __init__(
        self,
        heartbeat: int = 60,
        join_timeout: int = 1,
        loop_cb: callable = None,
        loop_kwargs: dict = None,
        logger=None,
    ):
        super(Daemon, self).__init__()

        self._manager = multiprocessing.Manager()
        self.start_signal = self._manager.Event()
        self.exit_signal = self._manager.Event()
        self.process = dict(main=self._process_details())

        self.heartbeat = heartbeat
        self.join_timeout = join_timeout

        if loop_cb is None:
            self.loop_cb = self.wait_loop
        else:
            self.loop_cb = loop_cb

        if loop_kwargs is None:
            self.loop_kwargs = dict()
        else:
            self.loop_kwargs = loop_kwargs

        self.logger = logger or logging.getLogger(__name__)

    def _process_details(self) -> dict:
        """ Initialises the process entry dictionary """
        return dict(
            tx_queue=self._manager.Queue(queue_max_size),
            rx_queue=self._manager.Queue(queue_max_size),
            exit_signal=None,
            object=None,
            object_kwargs=None,
            runtime=dict(task=None, kwargs=None, as_daemon=None),
        )

    @property
    def manager(self) -> multiprocessing.Manager:
        """ Returns the manager object """
        return self._manager

    @property
    def queue(self, name, queue_name="rx_queue") -> multiprocessing.Queue:
        """ Returns a process queue """
        return self.process[name][queue_name]

    def create_shared_dict(self, **kwargs):
        """ Creates and returns a new manager dictionary """
        return self._manager.dict(**kwargs)

    def create_queue(self):
        """ Creates and returns a new manager queue """
        return self._manager.Queue(queue_max_size)

    def wait_loop(self):
        """ Default loop. Waits until an exit signal is given or the processes are dead"""
        try:
            while not self.exit_signal.is_set():
                for _, register in self.process.items():
                    try:
                        if not register["object"].is_alive():
                            if not self.exit_signal.is_set():
                                self.exit_signal.set()
                                break
                    except (KeyError, AttributeError):
                        pass
                time.sleep(self.heartbeat)
        except KeyboardInterrupt:
            pass

        if not self.exit_signal.is_set():
            self.exit_signal.set()

    def init_process(self, name):
        """ Initialises a process entry """
        if name not in self.process:
            self.process[name] = self._process_details()
            self.logger.debug("Creating message queues for %s", name)
        else:
            self.logger.debug("Message queues already created")

    def build(
        self,
        name: str,
        cls: callable,
        kwargs: dict,
        receive_from=None,
        send_to=None,
        storage=False,
        storage_name="mysql",
    ):
        """ Creates the object which will interact with the process """

        self.init_process(name)

        self.logger.info("Queues max size is {} items.".format(queue_max_size))

        if "start_signal" not in kwargs:
            kwargs["start_signal"] = self.start_signal

        kwargs["exit_signal"] = self.exit_signal

        # chose on which queue to put data to
        if send_to:
            self.logger.info(
                "%s sending messages to %s [rx_queue]", name, send_to
            )
            kwargs["tx_queue"] = self.process[send_to]["rx_queue"]
        else:
            if "tx_queue" not in kwargs:
                kwargs["tx_queue"] = self.process[name]["tx_queue"]

        # chose on which queue to get data from
        if receive_from:
            self.logger.info(
                "%s receiving messages from %s[tx_queue]", name, receive_from
            )
            kwargs["rx_queue"] = self.process[receive_from]["tx_queue"]
        else:
            if "rx_queue" not in kwargs:
                kwargs["rx_queue"] = self.process[name]["rx_queue"]

        if storage:
            kwargs["storage_queue"] = self.process[storage_name]["rx_queue"]

        if self.logger:
            kwargs["logger"] = self.logger

        obj = cls(**kwargs)
        self.process[name]["object"] = obj
        self.process[name]["object_kwargs"] = kwargs
        try:
            self.process[name]["runtime"]["task"] = obj.run
        except AttributeError:
            self.logger.warning(
                "Object does not have a run method. Runtime task undefined!"
            )

        self.process[name]["runtime"]["kwargs"] = dict()
        self.process[name]["runtime"]["as_daemon"] = True
        return obj

    def set_run(self, name, task=None, task_kwargs=None, task_as_daemon=None):
        """ Sets the run time task for a given object """

        if task is not None:
            self.process[name]["runtime"]["task"] = task

        if task_kwargs is not None:
            self.process[name]["runtime"]["kwargs"] = task_kwargs

        if task_as_daemon is not None:
            self.process[name]["runtime"]["as_daemon"] = task_as_daemon

    def set_loop(self, cb, cb_kwargs=None):
        """ Sets the loop callback and its arguments """
        self.loop_cb = cb
        if cb_kwargs is not None:
            self.loop_kwargs = cb_kwargs

    def start(self, set_start_signal=False):
        """ Starts the processes and executes the loop """

        self.init_processes()

        if set_start_signal:
            self.start_signal.set()

        self.run_processes()
        self.shutdown_processes()

        self.logger.debug("daemon has left")

    def init_processes(self):
        for name, register in self.process.items():
            if "main" in name:
                continue
            try:
                # creates multiprocessing object
                register["runtime"]["object"] = multiprocessing.Process(
                    target=register["runtime"]["task"],
                    kwargs=register["runtime"]["kwargs"],
                    daemon=register["runtime"]["as_daemon"],
                )

                register["runtime"]["object"].start()
            except (KeyError, TypeError):
                self.logger.exception("Failed to start services")
                raise

    def shutdown_processes(self):
        for name, register in self.process.items():
            self.logger.debug("daemon killing %s", name)
            if "main" in name:
                continue
            try:
                if register["runtime"]["object"].is_alive():
                    register["runtime"]["object"].terminate()
                    register["runtime"]["object"].join(
                        timeout=self.join_timeout
                    )

            except Exception as err:
                self.logger.exception("error killing %s: %s", name, err)
                continue

    def run_processes(self):
        try:
            self.logger.debug("entering daemon's wait loop: %s", self.loop_cb)
            self.loop_cb(**self.loop_kwargs)
        except KeyboardInterrupt:
            try:
                self.exit_signal.set()
            except ConnectionResetError:
                pass

        except Exception as err:
            self.logger.exception(
                "main execution loop exited with error %s", err
            )
            if not self.exit_signal.is_set():
                try:
                    self.exit_signal.set()
                except ConnectionResetError:
                    pass
