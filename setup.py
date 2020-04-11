"""
    Wirepas Gateway Client
    ======================

    Installation script

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme_file = "README.md"
license_file = "LICENSE"
requirements_file = "requirements.txt"

with open(readme_file) as f:
    long_description = f.read()


def custom_scheme():
    def custom_version(version):
        tag = str(version.tag)
        if version.exact:
            return tag

        # split on rc and compute a pre-release tag for the next patch
        tag_components = tag.rsplit("rc")
        major, minor, patch = tag_components[0].split(".")
        patch = int(patch) + 1
        distance = version.distance
        tag = f"{major}.{minor}.{patch}.dev{distance}"

        return tag

    return {
        "version_scheme": custom_version,
        "local_scheme": "no-local-version",
        "write_to": "version.py",
        "fallback_version": str(fallback_version["version"]),
    }


def get_absolute_path(*args):
    """ Transform relative pathnames into absolute pathnames """
    return os.path.join(here, *args)


def get_requirements(*args):
    """ Get requirements requirements.txt """
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r"^#.*|\s#.*", "", line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r"\s+", "", line))
    return sorted(requirements)


fallback_version = {}
try:
    with open(get_absolute_path("./version.py")) as f:
        exec(f.read(), fallback_version)
except FileNotFoundError:
    fallback_version["version"] = "0.1.0"


about = {}
with open(get_absolute_path("./wirepas_backend_client/__about__.py")) as f:
    exec(f.read(), about)

setup(
    name=about["__pkg_name__"],
    use_scm_version=custom_scheme,
    setup_requires=["setuptools_scm"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    license=about["__license__"],
    classifiers=about["__classifiers__"],
    keywords=about["__keywords__"],
    packages=find_packages(exclude=["contrib", "docs", "tests", "examples"]),
    install_requires=get_requirements(requirements_file),
    include_package_data=True,
    package_dir={
        "wirepas_backend_client.messages": "wirepas_backend_client/messages"
    },
    package_data={
        "wirepas_backend_client.messages": ["decoders/diagnostics.json"]
    },
    data_files=[
        (
            "./wirepas_backend_client-extras/package",
            ["LICENSE", "README.md", "requirements.txt", "setup.py"],
        ),
        (
            "./wirepas_backend_client-extras/examples",
            [
                "examples/find_all_nodes.py",
                "examples/influx_viewer.py",
                "examples/mqtt_viewer.py",
            ],
        ),
    ],
    entry_points={
        "console_scripts": [
            "wm-gw-cli=wirepas_backend_client.__main__:gw_cli",
            "wm-wnt-viewer=wirepas_backend_client.__main__:wnt_client",
            "wm-wpe-viewer=wirepas_backend_client.__main__:wpe_client",
            "wm-wps=wirepas_backend_client.__main__:provisioning_server",
        ]
    },
)
