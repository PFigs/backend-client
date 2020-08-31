import json
import wirepas_messaging
import datetime

from wirepas_backend_client.tools import LoggerHelper
from wirepas_backend_client.messages.interface import MessageManager

LoggerHelper(module_name="message_decoding").setup()


# flake8: noqa

# these methods are to be migrated to the MESH interface
def is_low_latency(role, definition):
    mode = role & definition["ll"]
    return mode == definition["ll"]


def is_headnode(role, definition):
    return _is_role(role, "headnode", definition)


def is_subnode(role, definition):
    return _is_role(role, "subnode", definition)


def is_sink(role, definition):
    return _is_role(role, "sink", definition)


def _is_role(role, name, definition):
    role = role & definition["baserole_mask"]
    return role == definition[name]


def get_traffic(filepath):
    with open(filepath) as input_file:
        messages = input_file.readlines()
    return messages


def get_role_fields(filepath):
    with open(filepath) as input_file:
        data = json.load(input_file)
    return data


def build_wire_message(record):
    wire_message = wirepas_messaging.gateway.api.ReceivedDataEvent(
        record["gw_id"],
        record["sink_id"],
        int(
            datetime.datetime.fromisoformat(record["rx_time"]).timestamp()
            * 1e3
        ),
        record["source_address"],
        record["destination_address"],
        record["source_endpoint"],
        record["destination_endpoint"],
        record["travel_time_ms"],
        record["qos"],
        bytes.fromhex(record["data_payload"]),
        hop_count=record["hop_count"],
    )
    return wire_message


def parse_wire_message(message):
    parsed_message = MessageManager.map(
        message.source_endpoint, message.destination_endpoint
    ).from_bus(message.payload)
    return parsed_message


def assert_diagnostic_role_content(apdu, role, fields):
    found_fields = list()
    for key, value in apdu.items():
        for field in fields[role]:
            if key in field:
                found = True
                found_fields.append(field)
                break

        if not found:
            raise ValueError(f"missing content for {role}: {key}")

    decoded = set(apdu.keys())
    discovered = set(found_fields)

    # fields that might be zero and implicitly set
    decoded.add("cbmac_details")
    discovered.add("cbmac_details")

    print(f"APDU len: {len(decoded)} == FOUND len: {len(found_fields)})")
    if decoded != discovered:
        print(f"decoded: {decoded}")
        print(f"discovered: {discovered}")
        # fields that have been discovered but are not in the decoded
        extra = discovered - decoded
        missing = decoded - discovered
        print(f"Extra in discovered: {extra}")
        print(f"Missing in decoded: {missing}")
        raise ValueError(f"Unreported fields within message {role}")


def test_dreq_content():
    """
    This takes recorded mqtt traffic and checks
    that the protobuff message can be regenerated
    and that its decoding results in the same object
    """

    stack_roles = dict(
        invalid=0x00,
        sink=0x01,
        headnode=0x02,
        subnode=0x03,
        baserole_mask=0x0F,
        ll=0x10,
        autorole=0x80,
        mode_mask=0xF0,
    )

    dualmcu_roles = dict(
        sink=0x04,
        headnode=0x02,
        subnode=0x01,
        baserole_mask=0x0F,
        ll=0x10,
        autorole=0x80,
        mode_mask=0xF0,
    )

    roles_map = dualmcu_roles

    messages = get_traffic("./unit_tests/files/received_messages.json")

    for message in messages:

        message = message.strip("\n")
        if not message:
            continue

        record = json.loads(message)
        wire_message = build_wire_message(record)
        parsed_message = parse_wire_message(wire_message)
        diagnostic_fields = get_role_fields(
            "./unit_tests/definitions/role_field_dreq.json"
        )

        if (
            parsed_message.source_endpoint == 247
            and parsed_message.destination_endpoint == 255
        ):
            if "trace_options" not in parsed_message.apdu:
                continue

            if parsed_message.apdu["trace_options"]["trace_type"] != 2:
                continue

            if not parsed_message.apdu:
                print(f"ignoring payload:{parsed_message.data_payload.hex()}")
                continue

            if "role" not in parsed_message.apdu:
                continue

            role = parsed_message.apdu["role"]

            print(
                f"evaluating:  source_address={parsed_message.source_address}, role={role:x}"
            )

            if is_low_latency(role, roles_map):
                mode = "ll"
            else:
                mode = "le"

            if is_sink(role, roles_map):
                print(f"{mode} sink")
                assert_diagnostic_role_content(
                    parsed_message.apdu, f"{mode}_router", diagnostic_fields
                )

            elif is_headnode(role, roles_map):
                print(f"{mode} headnode")
                assert_diagnostic_role_content(
                    parsed_message.apdu, f"{mode}_router", diagnostic_fields
                )

            elif is_subnode(role, roles_map):
                print(f"{mode} subnode")
                assert_diagnostic_role_content(
                    parsed_message.apdu,
                    f"{mode}_non_router",
                    diagnostic_fields,
                )
            else:
                print("Unknown role")


if __name__ == "__main__":
    test_dreq_content()
