import json
import datetime

__DIAGNOSTIC_INTERVAL = 30 / 2


def compare_diagnostic_packets(mapping: dict, packets: dict) -> bool:
    """ Takes v1 and v2 field mappings and ensures that the contents match """

    for v2_field, v1_map in mapping.items():

        v1_field = v1_map["field"]
        v2_packet = packets[247]

        if v2_field in v2_packet:
            v2_content = v2_packet[v2_field]
        else:
            continue

        make_comparison = False
        for ep in packets:
            if v1_field in packets[ep]:
                v1_content = packets[ep][v1_field]
                make_comparison = True
                break

        if "blacklist" in v2_field:
            blacklist = (
                v2_content["ch_group_1"]
                | v2_content["ch_group_2"] << 8
                | v2_content["ch_group_3"] << 16
                | v2_content["ch_group_4"] << 24
                | v2_content["ch_group_5"] << 32
            )
            v2_content = blacklist

        if make_comparison:
            if v2_content != v1_content:
                if v1_map["match"]:
                    print(
                        f"Mismatch between {v2_field} != {v1_field} ({v2_content} != {v1_content})"
                    )
                else:
                    print(
                        f"Expected mismatch between {v2_field} != {v1_field} ({v2_content} != {v1_content})"
                    )
            else:
                pass
                # print(f"OK {v2_field} == {v1_field} ({v2_content} == {v1_content})")


def test_v1_v2_content():
    """ Asserts the match or mismatch between diagnostic packets' content """

    with open("./unit_tests/definitions/v1_v2.json") as mapping_instructions:
        mapping = json.load(mapping_instructions)

    with open("./unit_tests/files/v1_v2_traces.json") as mqtt_traffic:
        messages = mqtt_traffic.readlines()

    delta = __DIAGNOSTIC_INTERVAL * 10

    packet_time = dict()
    diagnostic_packets = dict()
    previous_packet_time = dict()

    for message in messages:

        message = message.strip("\n")
        if not message:
            continue
        try:
            record = json.loads(message)
        except:
            print(message)
            continue
        source = record["source_address"]
        packet_time[source] = datetime.datetime.fromisoformat(
            record["rx_time"]
        )

        if source not in diagnostic_packets:
            diagnostic_packets[source] = dict()
        if source not in previous_packet_time:
            previous_packet_time[source] = dict()

        if previous_packet_time[source]:

            if source in previous_packet_time:
                delta = packet_time[source] - previous_packet_time[source]

            if delta.total_seconds() < __DIAGNOSTIC_INTERVAL:
                diagnostic_packets[source][record["source_endpoint"]] = record
            else:
                if (
                    len(diagnostic_packets[source]) > 2
                    and 247 in diagnostic_packets[source]
                ):
                    compare_diagnostic_packets(
                        mapping, diagnostic_packets[source]
                    )
                diagnostic_packets[source] = dict()
                diagnostic_packets[source][record["source_endpoint"]] = record

        previous_packet_time[source] = packet_time[source]


if __name__ == "__main__":
    test_v1_v2_content()
