import json
import wirepas_messaging
import datetime
from wirepas_backend_client.tools import LoggerHelper

from wirepas_backend_client.messages.interface import MessageManager

LoggerHelper(module_name="message_decoding").setup()


def decode_apdu():

    with open("./unit_tests/files/apdu_decode.json") as mqtt_traffic:
        messages = mqtt_traffic.readlines()

    for message in messages:
        record = json.loads(message)

        if "gw_id" not in record:
            record["gw_id"] = "gw_id"
        if "sink_id" not in record:
            record["sink_id"] = "sink_id"
        if "rx_time" not in record:
            record["rx_time"] = int(datetime.datetime.now().timestamp() * 1e3)
        if "source_address" not in record:
            record["source_address"] = "source_address"
        if "destination_address" not in record:
            record["destination_address"] = "destination_address"

        if "travel_time_ms" not in record:
            record["travel_time_ms"] = 0
        if "qos" not in record:
            record["qos"] = 0
        if "data_payload" not in record:
            record["data_payload"] = bytes.fromhex(record["data_payload"])
        if "hop_count" not in record:
            record["hop_count"] = 0

        wire_message = wirepas_messaging.gateway.api.ReceivedDataEvent(
            record["gw_id"],
            record["sink_id"],
            record["rx_time"],
            record["source_address"],
            record["destination_address"],
            record["source_endpoint"],
            record["destination_endpoint"],
            record["travel_time_ms"],
            record["qos"],
            bytes.fromhex(record["data_payload"]),
            hop_count=record["hop_count"],
        )

        parsed_message = MessageManager.map(
            wire_message.source_endpoint, wire_message.destination_endpoint
        ).from_bus(wire_message.payload)

        print(
            "<<<<<<<<<\n",
            f"source_ep: {wire_message.source_endpoint}\n",
            f"destination_ep: {wire_message.destination_endpoint}\n",
            f"payload length: {len(wire_message.data_payload)}\n"
            f"payload: {wire_message.data_payload}\n",
        )

        print("Print serialization")
        print(json.dumps(parsed_message.serialize(flat_keys=False), indent=4))

        print("Flatten keys")
        print(json.dumps(parsed_message.serialize(flat_keys=True), indent=4))

        try:
            print("Print cbor string")
            print(parsed_message.cbor_contents)
            print("=========")
        except AttributeError:
            pass


if __name__ == "__main__":
    decode_apdu()
