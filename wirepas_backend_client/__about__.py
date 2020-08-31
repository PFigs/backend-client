"""
    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from pkg_resources import get_distribution, DistributionNotFound

__author__ = "Wirepas Ltd"
__author_email__ = "opensource@wirepas.com"
__classifiers__ = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Topic :: Software Development :: Libraries",
    "Programming Language :: Python :: 3",
]
__copyright__ = "2020 Wirepas Ltd"
__description__ = "Interfaces to interact with Wirepas backend services."
__keywords__ = "wirepas connectivity iot mesh"
__license__ = "Apache-2"
__pkg_name__ = "wirepas_backend_client"
__title__ = "Wirepas Backend Client"
__url__ = "https://github.com/wirepas/backend-client"

try:
    __version__ = get_distribution(__pkg_name__).version
except DistributionNotFound:
    # package is not installed
    pass

