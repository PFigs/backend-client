import json
import wirepas_messaging
import datetime

from wirepas_backend_client.tools import LoggerHelper
from wirepas_backend_client.messages.interface import MessageManager

LoggerHelper(module_name="message_decoding").setup()


def get_traffic(filepath):
    with open(filepath) as mqtt_traffic:
        messages = mqtt_traffic.readlines()
    return messages


def build_wire_message(record):

    wire_message = wirepas_messaging.gateway.api.ReceivedDataEvent(
        gw_id=record["gw_id"],
        sink_id=record["sink_id"],
        rx_time_ms_epoch=int(
            datetime.datetime.fromisoformat(record["rx_time"]).timestamp()
            * 1e3
        ),
        src=record["source_address"],
        dst=record["destination_address"],
        src_ep=record["source_endpoint"],
        dst_ep=record["destination_endpoint"],
        travel_time_ms=record["travel_time_ms"],
        qos=record["qos"],
        data=bytes.fromhex(record["data_payload"]),
        data_size=record["data_size"],
        hop_count=record["hop_count"],
    )
    return wire_message


def parse_wire_message(message):
    parsed_message = MessageManager.map(
        message.source_endpoint, message.destination_endpoint
    ).from_bus(message.payload)
    return parsed_message


def test_exception_handling():
    """ This test ensures that incorrect payloads do not crash the decoder """

    messages = get_traffic(
        "./unit_tests/files/received_messages_incorrect_apdu.json"
    )

    for message in messages:
        message = message.strip("\n")
        if not message:
            continue
        record = json.loads(message)
        wire_message = build_wire_message(record)
        parse_wire_message(wire_message)


def test_received_messages():
    """
    This takes recorded mqtt traffic and checks
    that the protobuff message can be regenerated
    and that its decoding results in the same object
    """

    ignore_keys = ["network_id", "event_id", "received_at", "transport_delay"]

    stats = dict()
    messages = get_traffic("./unit_tests/files/received_messages.json")

    for message in messages:

        message = message.strip("\n")
        if not message:
            continue

        record = json.loads(message)
        wire_message = build_wire_message(record)
        parsed_message = parse_wire_message(wire_message)
        dmessage = parsed_message.serialize()

        print(
            "<<<",
            wire_message.source_endpoint,
            wire_message.destination_endpoint,
        )
        print(json.dumps(dmessage, indent=4))
        print("=========")

        for key in record:

            if key in ignore_keys:
                continue

            try:
                if record[key] != dmessage[key]:
                    raise ValueError(
                        "{}: {} != {}".format(key, record[key], dmessage[key])
                    )
            except KeyError:
                print(f"missing key: {key}")
                continue

        try:
            stats[
                "{}:{}".format(
                    wire_message.source_endpoint,
                    wire_message.destination_endpoint,
                )
            ] += 1
        except KeyError:
            stats[
                "{}:{}".format(
                    wire_message.source_endpoint,
                    wire_message.destination_endpoint,
                )
            ] = 1

    print("Endpoints and messages tested: {}".format(stats))


if __name__ == "__main__":
    test_received_messages()
    test_exception_handling()
