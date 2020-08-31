"""
    WNT Client
    ==========

    Simple example on how to communicate with the
    wirepas network tool services.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

from .handlers import Backend
from .settings import WNTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper


def main():
    """ Main entrypoint to connect and talk to a WNT instance """

    PARSER = ParserHelper(description="WNT client arguments")
    PARSER.add_file_settings()
    PARSER.add_wnt()
    PARSER.add_fluentd()

    SETTINGS = PARSER.settings(settings_class=WNTSettings)

    LOGGER = LoggerHelper(
        module_name="wm-wnt-viewer", args=SETTINGS, level=SETTINGS.debug_level
    ).setup()

    if SETTINGS.sanity():
        Backend(settings=SETTINGS, logger=LOGGER).run(False)
    else:
        print("There is something wrong with your WNT arguments.")
        print(SETTINGS)


if __name__ == "__main__":

    main()
