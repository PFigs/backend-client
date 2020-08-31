"""
    Main
    ====

    Defines the package's entrypoints.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import argparse

from wirepas_backend_client.api.wnt import wnt_main
from wirepas_backend_client.api.wpe import wpe_main
from wirepas_backend_client.cli import start_cli
from wirepas_backend_client.provisioning import prov_main


def wnt_client():
    """ launches the wnt client """
    wnt_main()


def gw_cli():
    """ launches the gateway client """
    start_cli()


def wpe_client():
    """ launches the wpe client """
    wpe_main()


def provisioning_server():
    """ launches the provisioning server """
    prov_main()


def start_backend_client():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", help="settings help")
    parser.parse_args()
    gw_cli()


if __name__ == "__main__":
    start_backend_client()
