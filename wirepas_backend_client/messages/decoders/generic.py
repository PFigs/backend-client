"""
    Generic
    =======

    Contains a generic interface to handle network to object translations.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import cbor2
import struct
import datetime
import logging

import wirepas_messaging

from ..types import ApplicationTypes
from wirepas_backend_client.tools import flatten


class GenericMessage(wirepas_messaging.gateway.api.ReceivedDataEvent):
    """
    Generic Message serves as a simple packet abstraction.

    The base class is inherited from wirepas_messaging (ReceivedDataEvent).

    This class offers a few common attributes such as:

        source_endpoint (int): the source endpoint
        destination_endpoint (int): the destination endpoint
        _apdu_format (string): the Struct format or a descriptive field
        _apdu_fields (dict): a dictionary containing the apdu fields

        type (enum): enum to facilitate message type evaluation
        rx_time (datetime): arrival time of the packet at the sink
        tx_time (datetime): departure time of the message from the node
        received_at (datetime): when the packet was received by the framework
        transport_delay (int): amount of seconds the packet traveled over the network
        decode_time (datetime): when the decoding was initiated
        apdu (dict): a dictionary with the payload contents
        serialization (str): a safe representation of the packet for transport

    The following attributes are inherited by the ReceivedDataEvent class
    in wirepas_messaging:
        data_payload
        gw_id
        sink_id
        network_id
        event_id
        rx_time
        tx_time
        source_address
        destination_address
        source_endpoint
        destination_endpoint
        travel_time_ms
        received_at
        qos
        data_payload
        data_size
        hop_count

    When inheriting the GenericMessage class you should always call its
    decode method. Often, the decoding will happen on the object initialization,
    but if you wish to do it explicitly at a later point you can do so.

    However, by calling the GenericMessage.decode you will benefit from
    the decode_time upkeep automatically, plus any other common attributes
    that might be added in the future.

    This class also offer a few utility methods, which are useful if your
    application deals with TLV or CBOR encoded payloads. The tlv decoder
    always requires that your implement the _tlv_value_decoder.

    """

    # dummy endpoints
    source_endpoint = 0
    destination_endpoint = 0

    _apdu_format = None
    _apdu_fields = None

    def __init__(self, *args, **kwargs):

        # attributes obtained from
        # wirepas_messaging.gateway.api.ReceivedDataEvent
        self.data_payload = None
        self.gw_id = None
        self.sink_id = None
        self.network_id = None
        self.event_id = None
        self.rx_time = None
        self.tx_time = None
        self.source_address = None
        self.destination_address = None
        self.source_endpoint = None
        self.destination_endpoint = None
        self.travel_time_ms = None
        self.received_at = None
        self.qos = None
        self.data_payload = None
        self.data_size = None
        self.hop_count = None

        super(GenericMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.GenericMessage
        self.decode_time = 0
        self.apdu = dict()

        # ensure data size is correct
        if self.data_payload is None:
            self.data_size = 0
            self.data_payload = bytes()
        else:
            self.data_size = len(self.data_payload)
            if isinstance(self.data_payload, str):
                self.data_payload = bytes(self.data_payload, "utf8")

        self.rx_time = datetime.datetime.utcfromtimestamp(
            self.rx_time_ms_epoch / 1e3
        )
        self.tx_time = self.rx_time - datetime.timedelta(
            seconds=self.travel_time_ms / 1e3
        )
        self.received_at = datetime.datetime.utcnow()

        # localize to UTC
        self.rx_time = self.rx_time.replace(tzinfo=datetime.timezone.utc)
        self.tx_time = self.tx_time.replace(tzinfo=datetime.timezone.utc)
        self.received_at = self.received_at.replace(
            tzinfo=datetime.timezone.utc
        )

        self.transport_delay = round(
            (self.received_at - self.tx_time).total_seconds() * 1e3, 2
        )
        self.serialization = dict()

    @property
    def logger(self):
        """
        Retrieves the message_decoding logger.

        If you wish the messages to show debug information, please
        remember to configure the logging prior to this call.

        """
        return logging.getLogger("message_decoding")

    @property
    def header(self):
        return self._serialization_common()

    @classmethod
    def from_bus(cls, d):
        """ Translates a bus message into a message object """
        if isinstance(d, dict):
            return cls.from_dict(d)

        return cls.from_proto(d)

    @classmethod
    def from_dict(cls, d: dict):
        """ Translates a dictionary a message object """
        obj = cls(**d)
        return obj

    @classmethod
    def from_proto(cls, proto):
        """ Translates a protocol buffer into a message object """
        obj = cls.from_payload(proto)
        return obj

    @staticmethod
    def map_list_to_dict(apdu_names: list, apdu_values: list):
        """
        Maps a list of apdu values and apdu names into a single dictionary.

        Args:
            apdu_name (list): list of apdu names
            apdu_values (list): list of apdu values

        """

        _apdu = dict()
        value_index = 0

        for name in apdu_names:
            try:
                _apdu[name] = apdu_values[value_index]
            except IndexError:
                # Detected more apdu_names than apdu_values.
                # By ignoring this, accept optional fields at end of message.
                break
            value_index += 1

        return _apdu

    @staticmethod
    def chunker(seq, size):
        """
            Splits a sequence in multiple parts

            Args:
                seq ([]) : an array
                size (int) : length of each array part

            Returns:
                array ([]) : a chunk of SEQ with given SIZE
        """
        return (seq[pos : pos + size] for pos in range(0, len(seq), size))

    @staticmethod
    def decode_hex_str(hexstr):
        """
            Converts a hex string with spaces and 0x handles to bytes
        """
        hexstr = hexstr.replace("0x", "")
        hexstr = hexstr.replace(" ", "").strip(" ")
        payload = bytes.fromhex(hexstr)
        return payload

    def emit_message(self, logger_cb, message):
        """ This method takes the logger level callback and emit a timed message"""
        header = self._serialization_common()
        header["message"] = message
        logger_cb(header)

    def decode(self):
        """ This method should always be called from whoever inherits it """
        self.decode_time = datetime.datetime.utcnow().isoformat("T")

    def cbor_decode(self, payload):
        """ Attempts to decode a cbor encoded payload and returns its contents """
        apdu = None
        try:
            apdu = cbor2.loads(payload)
        except cbor2.decoder.CBORDecodeError as err:
            self.logger.exception(err)
            self.emit_message(self.logger.error, str(err))

        return apdu

    def tlv_decoder(self, payload: bytes, tlv_header: str, tlv_fields: dict):
        """ Attempts to decode a tlv encoded payload and returns its contents """

        apdu = dict()
        start = 0
        end = 0

        tlv_header = struct.Struct(tlv_header)

        while True:
            # grab header
            start = end
            end = start + tlv_header.size

            if end >= self.data_size:
                break

            try:
                header = tlv_header.unpack(payload[start:end])
            except KeyError:
                self.logger.exception(
                    "Not enough bytes to index payload at %s->%s", start, end
                )
                break
            except struct.error as error:
                self.logger.exception(
                    "Could not decode tlv header: {}".format(error)
                )
                break

            # switch on type and unpack
            tlv_id = int(header[0])
            tlv_len = int(header[1])

            try:
                tlv_name = tlv_fields[tlv_id]["name"]
            except KeyError:
                self.logger.exception("Unknown TLV ID in payload: %s", tlv_id)
                continue

            try:
                tlv_field_format = struct.Struct(tlv_fields[tlv_id]["format"])
            except KeyError:
                self.logger.exception(
                    "TLV ID (%s) missing decoding format. Check your parser definition.",
                    tlv_id,
                )
                continue

            for _ in range(0, int(tlv_len / tlv_field_format.size)):

                start = end
                end = start + tlv_field_format.size

                try:
                    tlv_value = tlv_field_format.unpack(payload[start:end])
                except struct.error:
                    self.logger.exception(
                        "Could not decode TLV value from payload at %s -> %s",
                        start,
                        end,
                    )
                    continue

                self._tlv_value_decoder(
                    apdu, tlv_fields, tlv_id, tlv_name, tlv_value
                )

        return apdu

    def _tlv_value_decoder(
        self,
        apdu: bytes,
        tlv_fields: dict,
        tlv_id: int,
        tlv_name: str,
        tlv_value: list,
    ):
        """ This method should be implemented by the inheriting classes.
        It allows the handling of the tlv value list of values which are
        often implementation specific. """
        pass

    def _payload_serialization(self):
        """ Ensures the payload is a hex string. """
        try:
            return self.data_payload.hex()
        except AttributeError:
            return None

    def _apdu_serialization(self):
        """ Standard apdu serialization. """
        if self.apdu:
            for field in self.apdu:
                try:
                    self.serialization[field] = self.apdu[field]
                except KeyError:
                    pass

    def _serialization_common(self):
        """ Dictionary with common serialization header """

        header = {
            "gw_id": self.gw_id,
            "sink_id": self.sink_id,
            "network_id": self.network_id,
            "event_id": str(self.event_id),
            "rx_time": self.rx_time.isoformat("T"),
            "tx_time": self.tx_time.isoformat("T"),
            "source_address": self.source_address,
            "destination_address": self.destination_address,
            "source_endpoint": self.source_endpoint,
            "destination_endpoint": self.destination_endpoint,
            "travel_time_ms": self.travel_time_ms,
            "received_at": self.received_at.isoformat("T"),
            "qos": self.qos,
            "data_payload": self._payload_serialization(),
            "data_size": self.data_size,
            "hop_count": self.hop_count,
            "transport_delay": self.transport_delay,
        }

        return header

    def serialize(self, flat_keys=False, separator="/", prefix=""):
        """ Provides a generic serialization of the message"""

        self.serialization = self._serialization_common()
        self._apdu_serialization()

        if flat_keys:
            self.serialization = flatten(self.serialization, separator, prefix)

        return self.serialization

    def __str__(self):
        """ returns the inner dict when printed """
        return str(self.serialize())
