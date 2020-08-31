"""
    MQTT options when sending messages
    ========

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from enum import Enum


class MQTTqosOptions(Enum):
    at_most_once = 0
    at_least_once = 1
    exactly_once = 2
