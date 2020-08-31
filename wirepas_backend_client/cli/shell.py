"""
    Shell
    =====

    Contains shells to connect to backend services.

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import datetime
import logging
import os
import readline
import select
import subprocess
import sys
import time
import queue
from threading import Lock
import threading
from threading import Timer
from wirepas_backend_client.api.mqtt import Topics
from wirepas_backend_client.cli.gateway import GatewayCliCommands


class GatewayShell(GatewayCliCommands):
    """
    GatewayShell

    Implements an interactive shell to talk with gateway services.

    Attributes:
        intro (str) : what is printed on the terminal upon initialisation
        prompt (str)

    """

    # pylint: disable=locally-disabled, invalid-name, too-many-arguments,
    # pylint: disable=locally-disabled, too-many-public-methods, unused-argument, too-many-function-args

    def __init__(
        self,
        shared_state,
        tx_queue,
        rx_queue,
        settings,
        data_queue=None,
        event_queue=None,
        timeout=10,
        histfile_size=1000,
        exit_signal=None,
        logger=None,
    ):

        self._prompt_base = "cli"
        self._prompt_format = "{} | {} > "
        self._reply_greeting = "<< message from"

        self._bstr_as_hex = True
        self._pretty_prints = False
        self._minimal_prints = False
        self._silent_loop = False
        self._max_queue_size = 1000
        self._max_data_queue_size = 1  # Data queues contains list messges

        self._file = None
        self._histfile = os.path.expanduser("~/.wm-shell-history")
        self._histfile_size = histfile_size

        self._tracking_loop_timeout = 1
        self._tracking_loop_iterations = float("Inf")
        self._raise_errors = False
        self._skip_replies = True

        super().__init__()

        self.settings = settings
        self.intro = self.intro.format(**self.settings.to_dict())
        self.prompt = self._prompt_format.format(
            datetime.datetime.now().strftime("%H:%M.%S"), self._prompt_base
        )

        self.request_queue = tx_queue
        self.response_queue = rx_queue
        self.data_queue = data_queue
        self.event_queue = event_queue

        self.wait_api_lock = Lock()
        self.mqtt_topics = Topics()
        self.exit_signal = exit_signal
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

        self.device_manager = shared_state["devices"]
        self._shared_state = shared_state
        self._flush_lock = threading.Lock()

        self.start_data_event_queue_peroidic_flush_timer()

    def start_data_event_queue_peroidic_flush_timer(self):
        self.data_event_flush_timer_interval_sec: float = 1.0
        self._perioidicTimer = Timer(
            self.data_event_flush_timer_interval_sec,
            self.__data_event_perioid_flush_timeout,
        ).start()

    def __data_event_perioid_flush_timeout(self):
        with self._flush_lock:
            self._trim_queues()
            self.start_data_event_queue_peroidic_flush_timer()

    @staticmethod
    def time_format():
        """ The prompt time format """
        return datetime.datetime.now().strftime("%H:%M.%S")

    @staticmethod
    def consume_queue(q, block=False, timeout=0):
        """ Exhaust a given queue until it is empty """
        while not q.empty():
            yield q.get(block=block, timeout=timeout)

    @staticmethod
    def strtobytes(payload):
        """ Handles the conversion of payload strings to bytes """
        try:
            payload = bytes.fromhex(payload)
        except ValueError:
            payload = bytes(payload, "utf-8")
        return payload

    @staticmethod
    def is_match(message, field, value):
        """ Checks if the class has an attribute that matches the provided field """
        match = True
        try:
            if value:
                match = bool(value == getattr(message, field))
        except AttributeError:
            pass
        return match

    @staticmethod
    def is_valid(args):
        """
        Returns True when all mandatory arguments have been set
        (not None)
        """
        for value in args.values():
            if value is None:
                return False
        return True

    @staticmethod
    def parse(line):
        """ Splits the command line in argument and options (kwargs) """
        args = line.split(" ")
        options = dict()
        delete_index = list()
        for arg in args:
            if "=" in arg:
                option = arg.split("=")
                options[option[0]] = option[1]
                delete_index.append(args.index(arg))

        list(map(args.pop, sorted(delete_index, reverse=True)))

        return args, options

    @staticmethod
    def get_option(option, index, cast, args, kwargs):
        """ Obtains the argument based on its key or through its index """

        if option in kwargs:
            return cast(kwargs[option])

        try:
            return cast(args[index])
        except IndexError:
            return None

    def retrieve_args(self, line, options=None):
        """
        Retrieve args parses the line for the provided command options.

        Arguments:
            line (str): the command line
            options (dict): a dictionary with the expected options

        Return:
            A dictionary with the parsed arguments

        """
        args, kwargs = self.parse(line)
        index = 0
        params = dict()

        if options:
            for name, details in options.items():

                try:
                    value = self.get_option(
                        name,
                        index=index,
                        cast=details["type"],
                        args=args,
                        kwargs=kwargs,
                    )
                except ValueError:
                    value = None

                if value is None and "default" in details:
                    value = details["default"]

                params[name] = value
                index += 1

        return params

    def consume_response_queue(self):
        """ Exhausts the response queue """
        for message in self.consume_queue(self.response_queue):
            self.on_response_queue_message(message)
            yield message

    def get_message_from_response_queue(self):
        message = None
        if self.response_queue.empty() is not True:
            message = self.response_queue.get()
        return message

    def consume_data_queue(self):
        """ Exhausts the data queue """
        while self.get_messages_from_data_queue() is not None:
            pass

    def get_messages_from_data_queue(self) -> list:
        msgs = None
        # Data message rate is huge compared to others. Queue contains message
        # lists that are then processed
        if self.data_queue.empty() is False:
            msgs = self.data_queue.get()  # returns message list
        return msgs

    def consume_event_queue(self):
        """ Exhausts the event queue """
        for message in self.consume_queue(self.event_queue):
            self.on_event_queue_message(message)
            yield message

    def get_message_from_event_queue(self):
        message = None
        if self.event_queue.empty() is not True:
            message = self.event_queue.get()
        return message

    def _trim_queues(self):
        """ Trim queues ensures that queue size does not run too long"""
        try:
            if self.data_queue.qsize() > self._max_data_queue_size:
                self.consume_data_queue()

            if self.event_queue.qsize() > self._max_queue_size:
                self.consume_event_queue()

            if self.response_queue.qsize() > self._max_queue_size:
                self.consume_response_queue()
        except FileNotFoundError:
            sys.exit("Exiting")

    def _update_prompt(self):
        """ Method called to update the prompt command line.
            Parent classes should overload the on_update_prompt
        """
        super().on_update_prompt()

    def _tracking_loop(
        self, cb, timeout=None, iterations=None, silent=False, **kwargs
    ):
        """ Simple tracking loop for period cli tasks """

        if timeout is None:
            timeout = self._tracking_loop_timeout

        if iterations is None:
            iterations = self._tracking_loop_iterations

        n_iter = 0
        while n_iter < iterations:
            n_iter = n_iter + 1

            if not silent or self._silent_loop is True:
                print(
                    "#{} : {}".format(
                        n_iter, datetime.datetime.now().isoformat("T")
                    )
                )

            cb(**kwargs)

            i, _, _ = select.select([sys.stdin], [], [], timeout)
            if i:
                sys.stdin.readline().strip()
                return True

    def _print(self, reply, reply_greeting=None, pretty=None):
        """ Prettified reply """
        super().on_print(reply, reply_greeting=None, pretty=None)

    def wait_for_answer(self, device, request_message, timeout=30, block=True):
        """ Wait response to request_message. If response received, return it.
            If timeout, return None

            !Note this function will discard messages it gets from queue.
            """

        self.wait_api_lock.acquire()

        wait_start_time = time.perf_counter()

        if device is None:
            raise ValueError
        if request_message is None:
            raise ValueError

        message = None
        if timeout:
            response_good: bool = False

            while response_good is False:
                try:
                    queue_poll_time_sec: float = 0.1
                    message = self.response_queue.get(
                        block=block, timeout=queue_poll_time_sec
                    )
                    if str(message.gw_id) == str(device):
                        if int(message.req_id) == int(
                            request_message["data"].req_id
                        ):
                            response_good = True
                        else:
                            pass

                    else:
                        pass

                    if self.request_queue.empty():
                        # wait a bit to avoid busy loop when putting
                        # same message back and reading it again.
                        default_sleep_time: float = 0.1
                        time.sleep(default_sleep_time)

                except queue.Empty:
                    # keep polling
                    pass

                if time.perf_counter() - wait_start_time > timeout:
                    print(
                        "Error got no reply for {} in time. "
                        "Time waited {:.0f} secs.".format(
                            device, time.perf_counter() - wait_start_time
                        )
                    )
                    message = None
                    break

        self.wait_api_lock.release()
        return message

    def notify(self):
        """
        Notify sets the shared dictionary to propagate changes to the other
        processes
        """
        self._shared_state["devices"] = self.device_manager

    def disabled_do_toggle_print_minimal_information(self, line):
        """
        Switches the byte prints as hex strings or python byte strings
        """
        self._minimal_prints = not self._minimal_prints
        print("Minimal prints: {}".format(self._minimal_prints))

    def disabled_do_toggle_byte_print(self, line):
        """
        Switches the byte prints as hex strings or python byte strings
        """
        self._bstr_as_hex = not self._bstr_as_hex
        print("hex prints: {}".format(self._bstr_as_hex))

    def disabled_do_toggle_pretty_print(self, line):
        """
        Switches between json or pretty print
        """
        self._pretty_prints = not self._pretty_prints
        print("pretty prints: {}".format(self._pretty_prints))

    def disabled_do_toggle_silent_loop(self, line):
        """
        Enables/disables the tracking loop verbosity
        """
        self._silent_loop = not self._silent_loop
        print("track loop prints: {}".format(self._silent_loop))

    def disabled_do_toggle_raise_errors(self, line):
        """ Sets the raise error toggle """
        self._raise_errors = not self._raise_errors
        print("raise errors: {}".format(self._raise_errors))

    def disabled_do_set_loop_iterations(self, line):
        """
        Sets the amount of loop iterations
        """
        options = dict(
            iterations=dict(type=int, default=self._tracking_loop_iterations)
        )
        args = self.retrieve_args(line, options)

        self._tracking_loop_iterations = args["iterations"]
        print(
            "track loop iterations: {}".format(self._tracking_loop_iterations)
        )

    def disabled_do_set_loop_timeout(self, line):
        """
        Sets the loop evaluation time
        """
        options = dict(
            timeout=dict(type=int, default=self._tracking_loop_timeout)
        )
        args = self.retrieve_args(line, options)

        self._tracking_loop_timeout = args["timeout"]
        print("track loop timeout: {}".format(self._tracking_loop_timeout))

    def disabled_do_set_reply_greeting(self, line):
        """
        Sets the reply greeting
        """

        if line.lower() in ("", "none", " "):
            line = None

        self._reply_greeting = line
        print("reply greeting set to: {}".format(self._reply_greeting))

    def do_settings(self, line):
        """
        Prints outs the settings acquired upon starting
        """
        self._print(self.settings, reply_greeting="settings:")

    def do_bye(self, line):
        """
        Exits the cli

        Usage:
            bye
        """
        print("Thank you for using Wirepas Gateway Client")
        self.close()
        if not self.exit_signal.is_set():
            self.exit_signal.set()

        return True

    def do_q(self, line):
        """
        Exits the cli

        Usage:
            q
        """
        return self.do_bye(line)

    def disabled_do_eof(self, line):
        """ Captures CTRL-D """
        return self.do_bye(line)

    def disabled_do_EOF(self, line):
        """ Captures CTRL-D """
        return self.do_bye(line)

    def disabled_do_record(self, arg="shell-session.record"):
        """
        Saves typed commands in a file for later playback

        Usage:
            record [filename (default: shell-session.record)]
        """
        self.close()
        self._file = open(arg, "w")

    def disabled_do_playback(self, arg="shell-session.record"):
        """
        Plays commands from a file

        Usage:
            plaback [filename (default: shell-session.record)]
        """
        try:
            with open(arg) as f:
                lines = f.read().splitlines()
                if "bye" in lines[-1]:
                    del lines[-1]
                self.cmdqueue.extend(lines)
        except TypeError:
            print("wrong file name")

    def do_help(self, command, args=None):
        """ Prints the command help and the acquired arguments (if given)"""
        # pylint: disable=locally-disabled, arguments-differ
        if args is not None:
            print(f"insufficient/incorrect arguments: {args}")
        super().do_help(command)

    @staticmethod
    def do_shell(line):
        """ Escape shell commands with! """
        args = line.split()
        try:
            output = subprocess.check_output(args, shell=False)
            print(output.decode())
        except FileNotFoundError:
            print("Unknown shell command: {}".format(args))

    def emptyline(self):
        """ What happens when an empty line is provided """
        self.consume_response_queue()

    def precmd(self, line):
        """ Executes before a command is run in onecmd """
        with self._flush_lock:  # Either we flush queue or process command
            self.device_manager = self._shared_state["devices"]

            if (
                self._file
                and "playback" not in line
                and "bye" not in line
                and "close" not in line
            ):
                print(line, file=self._file)

            if self._shared_state["devices"]:
                self.consume_response_queue()
                self._update_prompt()

        return line

    def postcmd(self, stop, line):
        """ Method called after each command is executed """
        with self._flush_lock:  # Either we flush queue or process command
            if self._shared_state["devices"]:
                self._update_prompt()
        return stop

    def onecmd(self, line):
        """
            Executes each command, escaping it for errors and updates the
            prompt with the current time and selection identifiers.

        """
        # pylint: disable=locally-disabled, broad-except
        with self._flush_lock:  # Either we flush queue or process command
            if self.exit_signal.is_set():
                return self.do_bye(line)

            try:
                if self.device_manager:
                    return super().onecmd(line)
            except Exception as err:
                print("Something went wrong:{}".format(err))
                if self._raise_errors:
                    raise

        return False

    def preloop(self):
        """ runs before the cmd loop is started """
        if os.path.exists(self._histfile):
            readline.read_history_file(self._histfile)

    def postloop(self):
        """ runs when the cmd loop finishes """
        readline.set_history_length(self._histfile_size)
        readline.write_history_file(self._histfile)

    def close(self):
        """
        Terminates the playback recording
        """
        if self._file:
            self._file.close()
            self._file = None
