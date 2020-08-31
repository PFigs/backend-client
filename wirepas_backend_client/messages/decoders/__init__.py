"""

    classDiagram
    ReceivedData <|-- GenericMessage
    GenericMessage: enum type
    GenericMessage: datetime rx_time
    GenericMessage: datetime tx_time
    GenericMessage: datetime received_at
    GenericMessage: float transport_delay
    GenericMessage: dattime decode_time
    GenericMessage: bytes apdu
    GenericMessage: dict serialization

    GenericMessage: source_endpoint()
    GenericMessage: destination_endpoint()
    GenericMessage: source_endpoint()
    GenericMessage: destination_endpoint()
    GenericMessage: logger()
    GenericMessage: from_bus()
    GenericMessage: from_dict()
    GenericMessage: from_proto()
    GenericMessage: map_list_to_dict()
    GenericMessage: chunker()
    GenericMessage: decode_hex_str()
    GenericMessage: decode()
    GenericMessage: cbor_decode()
    GenericMessage: tlv_decoder()
    GenericMessage: _tlv_value_decoder()
    GenericMessage: _payload_serialization()
    GenericMessage: _apdu_serialization()
    GenericMessage: serialize()

    ReceivedData: data_payload
    ReceivedData: gw_id
    ReceivedData: sink_id
    ReceivedData: network_id
    ReceivedData: event_id
    ReceivedData: rx_time
    ReceivedData: tx_time
    ReceivedData: source_address
    ReceivedData: destination_address
    ReceivedData: source_endpoint
    ReceivedData: destination_endpoint
    ReceivedData: travel_time_ms
    ReceivedData: received_at
    ReceivedData: qos
    ReceivedData: data_payload
    ReceivedData: data_size
    ReceivedData: hop_count

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from .generic import GenericMessage

# application/features
from .advertiser import AdvertiserMessage
from .positioning import PositioningMessage
from .ruuvi import RuuviMessage

# mesh diagnostics and test messages
from .diagnostics import DiagnosticsMessage
from .bootdiagnostics import BootDiagnosticsMessage
from .neighbordiagnostics import NeighborDiagnosticsMessage
from .trafficdiagnostics import TrafficDiagnosticsMessage
from .nodediagnostics import NodeDiagnosticsMessage

__all__ = [
    "GenericMessage",
    "AdvertiserMessage",
    "PositioningMessage",
    "RuuviMessage",
    "DiagnosticsMessage",
    "BootDiagnosticsMessage",
    "NeighborDiagnosticsMessage",
    "TrafficDiagnosticsMessage",
    "NodeDiagnosticsMessage",
]
