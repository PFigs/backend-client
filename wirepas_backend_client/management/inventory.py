"""
    Inventory
    =========

    Contains an inventory class that serves as an helper for the
    adv kpi

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import collections
import datetime
import logging
import math
import time


class Inventory(object):
    """
    Inventory

    This class serves as an helper to establish a count of devices based on
    their appearance.

    Attributes:
        _nodes(set): contains a set of nodes
        _index(set): dictionary which stores all the node events
        _target_nodes (set): which nodes to observe (None if not known)
        _target_otap_sequence (int): scratchpad sequence to observe in all nodes
        _target_frequency (int) : how many times a given node should be seen
        _start_delay (float) : how long to delay the counting
        _maximum_duration (float) : maximum duration of an inventory count
        _sequence (int) : inventory round
        _start (datetime): when to start
        _deadline (datetime) : when to end the test
        _finish (datetime) : when the test has finished
        _elapsed (float) : how many seconds it took to execute the inventory
        _otaped_nodes (set): which nodes have received an otap
        _runtime (float): how long the inventory has been running for
        logger(logging.logger): the logger where debug is routed to

    """

    # pylint: disable=locally-disabled, too-many-public-methods, too-many-instance-attributes, too-many-arguments
    # pylint: disable=locally-disabled, invalid-name

    def __init__(
        self,
        target_nodes=None,
        target_otap_sequence=None,
        target_frequency=None,
        start_delay=None,
        maximum_duration=None,
        logger=None,
    ) -> "Inventory":
        super(Inventory, self).__init__()

        self._target_nodes = target_nodes
        if self._target_nodes is None:
            self._target_nodes = set()

        self._target_otap_sequence = target_otap_sequence

        self._target_frequency = target_frequency
        if self._target_frequency is None:
            self._target_frequency = math.inf

        self._start_delay = start_delay
        self._maximum_duration = maximum_duration

        self._nodes = set()  # unique list of nodes
        self._index = dict()

        self._sequence = None
        self._start = None
        self._deadline = None
        self._finish = None
        self._elapsed = None
        self._otaped_nodes = set()
        self._runtime = None

        self.logger = logger or logging.getLogger(__name__)

    @property
    def start(self) -> datetime.datetime:
        """ Returns when the inventory has started """
        return self._start

    @property
    def deadline(self) -> datetime.datetime:
        """ Returns the inventory deadline """
        return self._deadline

    @property
    def elapsed(self) -> int:
        """ Returns how much time has elapsed since the start of the run """
        runtime = datetime.datetime.utcnow()
        if self._finish:
            runtime = self._finish
        self._runtime = (runtime - self._start).total_seconds()
        return self._runtime

    @property
    def sequence(self) -> int:
        """ Returns the current inventory sequence number """
        return self._sequence

    @sequence.setter
    def sequence(self, value):
        """ sets the sequence value """
        self._sequence = value

    @staticmethod
    def until(deadline: datetime) -> int:
        """ returns the amount of seconds until the next deadline"""
        now = datetime.datetime.utcnow()
        return (deadline - now).total_seconds()

    def finish(self):
        """ Procedure when an inventory has completed """
        self._finish = datetime.datetime.utcnow()
        return self._finish

    def reset(self):
        """ Clean up the internal variables to start over """
        self._nodes = set()  # unique list of nodes
        self._index = dict()

        self._start = None
        self._deadline = None
        self._finish = None
        self._elapsed = None

    def wait(self):
        """ waits until it the specified time """

        self.reset()

        now = datetime.datetime.utcnow()
        self._start = now + datetime.timedelta(seconds=self._start_delay)
        self._deadline = self._start + datetime.timedelta(
            seconds=self._maximum_duration
        )

        time_to_wait = (self._start - now).total_seconds()

        self.logger.debug(
            "waiting {} seconds to start".format(time_to_wait),
            dict(sequence=self.sequence),
        )
        time.sleep(time_to_wait)

    def add(
        self,
        node_address: int,
        rss: list = None,
        otap_sequence: list = None,
        timestamp: int = None,
    ) -> None:
        """
        Adds a node to the inventory

        Arguments:
            rss (list): a list of rss measurements to/from the device
            otap_sequence (list): a list of otap sequences registered by the device
            timestamp (int): a time representation

        """
        self._nodes.add(node_address)

        otap_min = None
        otap_max = None

        if otap_sequence:
            otap_min = min(otap_sequence)
            otap_max = max(otap_sequence)

        # creates an event
        if otap_min and otap_max and any(rss):
            event = dict(
                rss=rss,
                otap=otap_sequence,
                otap_max=max(otap_sequence),
                otap_min=min(otap_sequence),
            )
        elif any(rss):
            event = dict(rss=rss)

        elif any(otap_sequence):
            event = dict(
                otap=otap_sequence,
                otap_max=max(otap_sequence),
                otap_min=min(otap_sequence),
            )
        else:
            event = dict(rss=rss, otap=otap_sequence)

        # add nodes to index
        try:
            self._index[node_address]["count"] += 1
            self._index[node_address]["last_seen"] = timestamp
            self._index[node_address]["events"].append(event)

        except KeyError:
            self._index[node_address] = dict(
                last_seen=timestamp, events=[event], count=1
            )
            self.logger.debug(
                "adding node: {0} / {1}".format(node_address, event),
                dict(sequence=self.sequence),
            )

    def remove(self, node_address) -> None:
        """ Removes a node from the known inventory """
        self.nodes.remove(node_address)
        del self._index[node_address]

    def is_out_of_time(self):
        """ Evaluates if the time has run out for the run """
        time_left = self.until(self.deadline)
        self.logger.debug(
            "time left {}s ...".format(time_left), dict(sequence=self.sequence)
        )
        if time_left <= 0:
            return True
        return False

    def is_complete(self) -> bool:
        """
        Compares a set of nodes return true if they are the same
        or False otherwise
        """
        if not self._target_nodes or self._target_frequency < math.inf:
            return False

        if self._nodes.issuperset(self._target_nodes):
            if not self._target_otap_sequence:
                return True
        else:
            self.logger.critical(
                "elapsed {} - missing {}".format(
                    self.elapsed, self.nodes ^ self._target_nodes
                ),
                dict(sequence=self.sequence),
            )
            return False

        return False

    def is_otaped(self) -> bool:
        """
        Compares the ottaped nodes against the known nodes, returning True
        when the sets are the same and False otherwise.
        """
        if not self._target_nodes or self._target_otap_sequence is None:
            return False

        if not self.otaped_nodes.issuperset(self._target_nodes):
            self.logger.critical(
                "elapsed {} - otap missing {}".format(
                    self.elapsed, self.otaped_nodes ^ self._target_nodes
                ),
                dict(sequence=self.sequence),
            )
            return False

        return True

    def is_frequency_reached(self) -> bool:
        """
        Compares the node frequency against the predefined frequency
        target
        """
        if not self._target_nodes or self._target_frequency is None:
            return False

        frequency = self.frequency()
        if self._target_nodes:
            frequency = self._filter_dict(frequency)

        return all(
            map(lambda x: x >= self._target_frequency, frequency.values())
        )

    def _filter_dict(self, d: dict):
        """ Returns a dictionary that has keys occurring in _target_nodes """
        w = dict()
        for k, _ in d.items():
            if k in self._target_nodes:
                w[k] = d[k]
        return w

    def _account_for_target_nodes(self, d: dict):
        if self._target_nodes:
            for node in self._target_nodes:
                if node not in d:
                    d[node] = 0

    def difference(self):
        """ Returns the difference between seen nodes and target nodes """
        return self.nodes ^ self._target_nodes

    @property
    def target_nodes(self):
        """ Returns the target nodes to observe in the interface"""
        return self._target_nodes

    @property
    def target_otap_sequence(self):
        """ Returns the target otap to achieve"""
        return self._target_otap_sequence

    @property
    def target_frequency(self):
        """ Returns the target frequency (number of times) a node is seen"""
        return self._target_frequency

    @property
    def nodes(self):
        """ Returns the unique set of nodes observed so far"""
        return self._nodes

    @property
    def node(self, node_address):
        """ Retrieves information about a single node"""
        if node_address in self.nodes:
            return self._index[node_address]
        return None

    @property
    def otaped_nodes(self):
        """ Provides the set of nodes that have been ottaped to the target """
        self._otaped_nodes = set()
        for node_address, details in self._index.items():
            try:
                if (
                    details["events"][-1]["otap_min"]
                    == self._target_otap_sequence
                    or details["events"][-1]["otap_max"]
                    == self._target_otap_sequence
                ):
                    self._otaped_nodes.add(node_address)
            except KeyError:
                pass
        return self._otaped_nodes

    def frequency(self):
        """ Reports the node frequency"""
        frequency = dict()
        nodes = self._index.keys()
        for node in sorted(nodes):

            if self._target_otap_sequence:
                frequency[node] = self._index[node]["events"][-1]["otap_max"]
            else:
                frequency[node] = self._index[node]["count"]

        self._account_for_target_nodes(frequency)

        return frequency

    def frequency_by_value(self):
        """ Returns an ordered dictionary where frequency is used as a key"""
        frequency = dict()
        nodes = self._index.keys()
        max_value = 0
        for node in sorted(nodes):

            if self._target_otap_sequence:
                value = self._index[node]["events"][-1]["otap_max"]
            else:
                value = self._index[node]["count"]

            if value > max_value:
                max_value = value

            if value not in frequency:
                frequency[value] = set()
            frequency[value].add(node)

        ofreq = collections.OrderedDict()
        for key in sorted(frequency.keys()):
            ofreq["frequency_{0:03}".format(key)] = frequency[key]

        return ofreq

    def __str__(self):
        frequency = self.frequency_by_value()
        return str(frequency)
