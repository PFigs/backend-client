import pandas
import datetime

import wirepas_backend_client


def push_to_fluentd(df, logger):

    if args.fluentd_hostname:

        for row in df.iterrows():
            missing = set(row[1].inventory_target_nodes) ^ set(row[1].observed)

            record = dict(
                total_nodes=row[1].observed_total,
                missing=missing,
                inventory_start=datetime.datetime.utcfromtimestamp(
                    row[1].start / 1e3
                ).isoformat("T"),
                inventory_end=datetime.datetime.utcfromtimestamp(
                    row[1].end / 1e3
                ).isoformat("T"),
                elapsed=row[1].elapsed,
            )
            record["@timestamp"] = record["inventory_start"]
            logger.info(record)


if __name__ == "__main__":

    stats = dict()
    args = wirepas_backend_client.tools.parse_args()
    logger = wirepas_backend_client.tools.setup_log(
        "adv_test_history",
        fluentd_tag="python",
        fluentd_record="adv_test",
        fluentd_hostname=args.fluentd_hostname,
    )

    df = pandas.read_json(args.input)
    stats["elapsed"] = pandas.to_numeric(df.T.elapsed).describe()
    print(stats)

    push_to_fluentd(df.T, logger)
