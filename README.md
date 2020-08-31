# Backend-client

## Under consideration to be deprecated!

The current architecture of the backend client does not support easy addition of new features and there are quite many stability issues. Based on the initial analysis, major refactoring would be needed to make Backend client to support all the current use cases reliably. Hence, we are considering to break current backend client into focused functionalities that have value for wider community. This may imply that existing functionality is not supported anymore or it is supported in a new repository. More on this as work proceeds.









[![Codacy Badge](https://api.codacy.com/project/badge/Grade/bf0c23237cf04ea6ac48e98cf10b6a7b)](https://www.codacy.com/manual/wirepas/backend-client?utm_source=github.com&utm_medium=referral&utm_content=wirepas/backend-client&utm_campaign=Badge_Grade) [![Build Status](https://travis-ci.com/wirepas/backend-apis.svg?branch=master)](https://travis-ci.com/wirepas/backend-client)  [![Documentation Status](https://readthedocs.org/projects/backend-client/badge/?version=latest)](https://backend-client.readthedocs.io/en/latest/?badge=latest) [![PyPi](https://img.shields.io/pypi/v/wirepas-backend-client.svg)](https://pypi.org/project/wirepas-backend-client/)

<!-- MarkdownTOC levels="1,2,3" autolink="true"  style="ordered"  -->

1. [Introduction](#introduction)
1. [Installation](#installation)
    1. [Host dependencies](#host-dependencies)
    1. [Setting up a Python virtual environment](#setting-up-a-python-virtual-environment)
    1. [Installing from PyPi](#installing-from-pypi)
    1. [Installing from Github](#installing-from-github)
1. [Entrypoints](#entrypoints)
    1. [Gateway command line interface](#gateway-command-line-interface)
    1. [WPE Viewer](#wpe-viewer)
    1. [WNT Viewer](#wnt-viewer)
    1. [Provisioning server](#provisioning-server)
1. [Framework](#framework)
    1. [Structure](#structure)
    1. [Examples](#examples)
1. [Logging to fluentd](#logging-to-fluentd)
1. [Building and running over Docker](#building-and-running-over-docker)
    1. [Dockerhub](#dockerhub)
    1. [Running with docker](#running-with-docker)
    1. [Running with compose](#running-with-compose)
    1. [Building the image locally](#building-the-image-locally)
1. [Source documentation](#source-documentation)
1. [Contributing](#contributing)
1. [License](#license)

<!-- /MarkdownTOC -->

## Introduction

The Backend Client is a tool to serve as a decoder and a test framework
where you can extend the existing interfaces to develop your own test cases.
Interactions with
a [gateway][wirepas_gateway] must be compliant with the Wirepas
Backend to Gateway API.

In addition to the interaction with the Backend to Gateway Public API,
the Backend Client has also support for Wirepas Positioning Engine and Wirepas
Network Tool. Support for these tools is still work in progress
(see [milestones][backend_client_gh_milestones] and [projects][backend_client_gh_projects]).
However, you can already benefit from existing
entrypoints to help you capture data and debug your
integration (see [entrypoints](#entrypoints)).

Figure 1 illustrates the horizon where Backend Client is located.

![Architecture overview][here_img_overview]

**Figure 1** - Backend Client role in the Wirepas ecosystem.

## Installation

The Backend Client is written in python and it requires a valid MQTT
broker target to connect to, WNT or WPE credentials.

If you need help installing a MQTT broker or auxiliary software please
refer to our tutorials repository.

### Host dependencies

The main requirements of Backend Client are:

-   Python 3.7
-   Pip (we recommend the latest available)
-   Linux system

Certain Backend Client's dependencies must be
compiled locally upon installation,
thus require the installation of specific development headers.

Under Debian, the extra requirements are met with:

```bash
    sudo apt-get install default-libmysqlclient-dev gcc python3.7-dev
    
```

Please be advised that the name of such packages might change depending on your
Linux system. Please refer to the Dockerfiles
under the [container folder][here_container] for more detailed information.

Windows native environments are not supported. For help running the tool
in Windows, please use the Linux subsystem, Docker or a virtual machine.

### Setting up a Python virtual environment

As a recommendation, it is good practice to install and run the
application on a virtual python environment. Such approach avoids
possible issues with conflicting package versions.

We recommend you use [pipenv][pipenv]:

```shell
    pip3 install pipenv
```

If you choose to install and run the Backend Client inside a virtual
environment, please activate the environment before moving with the next
steps.

For pipenv, a virtual environment is created and activated by:

```shell
    pipenv --three
    pipenv shell
```

Once you activate your environment your can safely install the python
package under it.

For more information please refer to the tool's webpage.

### Installing from PyPi

The Backend Client is available from
[PyPi][backend_client_pypi] and you can install the latest stable version
with:

```shell
    pip install wirepas-backend-client
```

If you wish to install a particular version please see the release history
from PyPi.

### Installing from Github

First of all, make sure to clone the repository using the https address.

Checkout the
[git tag that corresponds to the release version][backend_client_gh_releases]
you want to install and install the package with:

```shell
    pip3 install .
```

If you leave your branch checked out to the top of master, it is likely that
you might run into a few issues. If you find them, please be so kind to
raise them to us through an [issue or bug report][backend_client_gh_issues].

If you want to develop or patch a bug under your local environment,
you can install the package in development mode through:

```shell
    pip3 install -e .
```

When installed in development mode, changes to the source files will be
immediately visible.

## Entrypoints

After installation, the Backend Client exposes several
[shell entrypoints][here_setup_entrypoints] that
can be run from any location in your system. This section describes their
usage in more detail.

### Gateway command line interface

The Backend Client exposes an interactive gateway command line which is
meant to interact with a gateway and sink pair connected to a given
MQTT broker.

To start an interactive command line to interact with a broker located
in your _localhost_ environment type:

```shell
    wm-gw-cli
```

Connecting to a remote server requires you to specify the values as an
argument or by reading from a yaml settings file. To view all the
arguments, please issue the command:

```shell
    wm-gw-cli --help
```

#### Connecting to the MQTT broker

For the gateway client to function properly, it needs to establish a
connection to the same MQTT broker where one or multiple gateways
are connected to.

To do so, let's assume the following MQTT credentials are saved in
./examples/settings.yml:

```yaml
 # examples/settings.yml
 # Example on how to set the MQTT credentials towards a local broker
 # with basic authentication
 mqtt_hostname: 127.0.0.1
 mqtt_password: password
 mqtt_username: username
 mqtt_port: 1883 # defaults to 8883 (secure port)
 mqtt_force_unsecure: True  # defaults to False (secure)
```

To start the gateway against the MQTT broker specified in
./examples/settings.yml, issue the following command:

```shell
    wm-gw-cli --settings ./examples/settings.yml
```

Once the client launches, you will be greeted with:

```shell
    Welcome to the Wirepas Gateway Client cli!
    Connecting to mosquittouser@127.0.0.1:1883 (unsecure: True)

    Type help or ? to list commands

    Type ! to escape shell commands
    Use Arrow Up/Down to navigate your command history
    Use CTRL-D or bye to exit

    09:50.17 | wm-gw-cli >
```

#### Commands

The gateway client has a set of commands which you can view by typing ?
in the client's shell:

```shell
    wm-gw-cli > ?

    Documented commands (type help <topic>):
    ========================================
    EOF                     playback           set_loop_iterations
    bye                     q                  set_loop_timeout
    clear_offline_gateways  record             set_reply_greeting
    eof                     scratchpad_status  set_sink
    gateway_configuration   scratchpad_update  settings
    gateways                scratchpad_upload  shell
    help                    selection          sinks
    list                    send_data          toggle_byte_print
    ls                      set_app_config     toggle_pretty_print
    networks                set_config         track_devices
    nodes                   set_gateway        track_data_packets
```

For each available command you can get more help if you type
**?command** for example, to view how to send a datagram,
type in the shell:

```shell
    wm-gw-cli > ?send_data
```

When typing commands, you can use the up and down arrows to browse your
shell history. There is also support for running host shell commands, by
prefacing the command with **!**.

#### Viewing connected devices

Upon a MQTT connection, the Backend Client will start populating an
internal structure based on any incoming message. The topic is parsed
and the information about the network devices are constructed.

The operation happens as messages are published from the network. It
will take time to build a full map of the network, which will be faster
depending on your network's packets per second.

In case you wish to view periodically which devices you have on your network,
type in the following command:

```shell
    wm-gw-cli > ?track_devices
```

To exit the tracking loop, give a new line feed to the input stream and
it will go back to the main command shell.

#### Device settings

When sending a downstream datagram, it is necessary to obey the
Backend to Gateway API (WM-RM-128).
For that reason, it is mandatory to know what is the target
gateway identifier and in most cases the sink id as well.

##### Selecting the target gateway and sink

The wm-gw-cli provides an easy way to select the target gateway and sink. To
make your choice, please type the following commands:

```shell
    wm-gw-cli > set_gateway
    0 : 2485378023427 : GatewayState.ONLINE
    1 : 2485378023426 : GatewayState.OFFLINE
    Please enter your gateway selection [0]: 0
    wm-gw-cli > set_sink
    0 : 3806491:2485378023427:sink0
    Please enter your sink selection [0]: 0
```

When setting the gateway, the wm-gw-cli shows you the following information
_object index : gateway id : state._ Similarly, for the sink, the wm-gw-cli
presents the object _index : network : gateway id: sink id_.

To make your selection, type the desired object index and press enter.

Once your selection is done, your commands will target that gateway id
and sink id. If you wish to view what your current selection is, use the
command:

```shell
    wm-gw-cli > selection
```

:warning: **WARNING** :warning:

The wm-gw-cli prompt will update itself with the current gateway and sink id.
Throughout this document, that information has been edited out of the
prompt.

##### Set app config

Setting the app config requires that your gateway and sink are selected.
In case you have not done the selection prior to this command, the wm-gw-cli
will ask for them.

When setting the app config, you are setting three values on the target
sink:

-   Diagnostic interval: the interval of network diagnostics (0, 30, 60,
    300, 600, 1800)

-   App config: A payload of a given size distributed to all associated
    devices on the network;

-   App config sequence: The sequence of the new app config (must be
    higher than the current one - otherwise the app config won't take
    effect, please refer to WM-RM-100).

The app config payload is given either as a set of binary data without
trailing 0x or as a utf8 data. For example, to send the
binary _0x10x40x5_ you should type _010405_.
If you simply want to have a text string on
your app config, you can for example type "sink by the window".

As an example, on the wm-gw-cli you would type:

```shell
    # Remember! no white spaces allowing in the payload!
    # If you want to toggle byte string to hex string in the
    # app_config_data, please see toggle_byte_print

    wm-gw-cli > set_app_config 10 sink_by_the_window 30
    answer <<
        gw_id: 2485378023427
        sink_id: sink0
        req_id: 12079559850249952277
        res: GatewayResultCode.GW_RES_OK
        sink_id: sink0
        current_ac_range_min: 2000
        current_ac_range_max: 8000
        min_ac: 2000
        max_ac: 8000
        max_mtu: 102
        min_ch: 1
        max_ch: 27
        hw_magic: 3
        stack_profile: 1
        app_config_max_size: 80
        are_keys_set: False
        firmware_version: [3, 4, 37, 0]
        node_role: 17
        node_address: 4193520
        network_address: 3806491
        network_channel: 22
        app_config_diag: 30
        app_config_seq: 10
        app_config_data:
        b'sink_by_the_window\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
        \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
        \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
        \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00
        \x00\x00\x00'
        channel_map: 286331153
        started: True
```

The answer will carry the gateway result and present you the new app
config.

##### Upload and process a scratchpad

The wm-gw-cli supports uploading a new scratchpad and asking the sink to take
it into use. _A full network OTAP is not currently supported with the
wm-gw-cli._ To initiate a network OTAP, you will have to send the
corresponding datagrams as mentioned in the remote API documentation.

The scratchpad commands are available as:

-   scratchpad_status
-   scratchpad_update
-   scratchpad_upload

:warning: **WARNING** :warning:

An incorrect scratchpad or an incorrect OTAP can damage your network
permanently. Please use these commands with care.

### WPE Viewer

The WPE viewer, _wm-wpe-viewer_, provides a simple way to check
if a WPE service and consume location updates for a given network.

The WPE viewer entrypoint requires correct population of the following
settings:

```yaml
    #examples/settings.yml
    wpe_service_definition: ./mywpesettings.json
    wpe_network: 1092 #optional
```

The _mywpesettings.json_ consists of a standard WPE client configuration
file. Please refer to WPE's official documentation for more details
on how to obtain and configure such file.

The wpe network is the network identifier on which your devices operate.
If you leave the parameter unset, the entrypoint will only perform a
ping to the backend specified under the json file.

### WNT Viewer

The WNT viewer, _wm-wnt-viewer_, provides a simple way to check
if a WNT service is reachable and to consume messages streamed by WNT on
its realtime metadata websocket. These message contain network and node
diagnostic information. Please refer to WNT's public API documentation
for further information.

The WNT viewer entrypoint requires correct population of the following
settings:

```yaml
    #examples/settings.yml
    wnt_username: "wntuser"
    wnt_password: "98asuyd907171ehjmasd"
    wnt_hostname: "wnthost.com"
```

### Provisioning server
The provisioning server, _wm-provisioning-server_, provides an example
implementation of the server side of the provisioning protocol. It must be used
with the _provisioning_joining_node_ application of the SDK. Please refer to
the provisioning reference manual for further information.

The Provisioning server entrypoint requires correct population of the following settings:

```yaml
    #examples/settings.yml
    mqtt_hostname: mqtt_broker_address_or_ip
    mqtt_password: password
    mqtt_username: username
    mqtt_port: 1883 # defaults to 8883 (secure port)
    mqtt_force_unsecure: True  # defaults to False (secure)

    provisioning_config: "./myprovisioningconfig.yml"
```

The _myprovisioningconfig.yml_ consists of a list of authorized nodes and their
associated provisioning data.

## Framework

Besides the useful entrypoints to interact with Wirepas services, the goal of
the Backend Client is to provide you a framework around which you can
build test cases to help you during your integration, research and
development phases.

### Structure

The framework or package is organized in several submodules:

1.  [api][bcli_api]
    1.  [api/influx][bcli_api_influx]
    2.  [api/mqtt][bcli_api_mqtt]
    3.  [api/mysql][bcli_api_mysql]
    4.  [api/wnt][bcli_api_wnt]
    5.  [api/wpe][bcli_api_wpe]
2.  [management][bcli_management]
3.  [mesh][bcli_mesh]
    1.  [mesh/interfaces][bcli_mesh_interfaces]
    2.  [mesh/interfaces/mqtt][bcli_mesh_interfaces_mqtt]
    3.  [mesh/interfaces/remote_api][bcli_mesh_interfaces_remote_api]
    4.  [mesh/interfaces/beacon_api][bcli_mesh_interfaces_beacon_api]
4.  [messages][bcli_messages]
5.  [test][bcli_test]
6.  [tools][bcli_tools]
7.  [cli](https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/cli)

#### API submodule

The [api submodule][bcli_api] contains the interfaces to connect
and handle data coming in and out of Wirepas' services and other
3rd party services such as databases
and message brokers.

Each API or interface folder is organized with connectors, handlers and
settings. The connectors file contains classes to establish a connection to
the target interface. The handlers contain classes to process streams of input
and output data. The settings file allows for handling parameter
translation from input to class arguments (if needed).

#### Management submodule

The [management submodule][bcli_management] contains files regarding
the runtime management of the framework.
In particular the daemon which simplifies the multiprocess aspect
of the Backend Client.

#### Mesh submodule

The [mesh submodule][bcli_mesh] contains files related to how
devices are mapped within the Backend Client.
In addition to those, the submodule contains an interfaces
folder which contains specializations on how to handle specific Wirepas's
APIs, such as the [Gateway to Backend API][bcli_mesh_interfaces_mqtt].

:pencil2: **NOTE** :pencil2:

In our redesign effort we are targeting to improve the device
classes and implement remote API support. Please follow the
framework development for more up to date information.

#### Messages submodule

The [messages submodule][bcli_messages] consists of a collection of
message handler or decoders that handle translation of known APDUS,
based on the endpoint they are associated to.

:pencil2: **NOTE** :pencil2:

We are considering moving the message handlers into the overarching Wirepas
Backend APIs project. Please follow the framework development for more up to
date information.

#### Test submodule

The [test submodule][bcli_test] contains classes to handle internal task
scheduling and scripts to address particular mesh use cases.

#### Tools submodule

The [tools submodule][bcli_tools] contains a collection of files
with classes that handle the acquisition of user
input, setup of the logging interface and general
purpose utility methods and classes.

#### Cli submodule

Currently still a [single file][wm_gw_cli], this upcoming submodule
will contain a re-factor of the gateway client to allow easier
customization and construction of custom command line interfaces.

## Logging to fluentd

The Backend Client has integrated logging with fluentd through Python's
logging facility.

Routing data to a fluentd host requires that you define the target host
when executing a Backend Client script.

To configure the target host, tag and record for the stream, ensure that
you configure the examples/settings.yml file with

```yaml
    # tags stream with app.mesh
    fluentd_hostname: "myfluenthost"
    fluentd_record: mesh
    fluentd_tag: app
```

## Building and running over Docker

Docker allows application to run on a sandbox containing
all the dependencies needed to run and execute them.
If you are not familiar with Docker, please refer to the
official documentation at [docker.com][docker].

### Dockerhub

Backend Client builds are available
from dockerhub under the [Backend Client registry][backend_client_dockerhub].

The latest tag points to the current stable release,
whereas the edge tag points to the top of master.

The latest tag is built automatically at dockerhub whenever this repository
is tagged.

The edge tag is built after each single merge into master.

To pull the Backend Client image from dockerhub use:

```shell
    docker pull wirepas/backend-client:latest
    docker pull wirepas/backend-client:<tag>
```

### Running with docker

As the container will have no access to your local environment, you will have
to propagate the input parameters by mounting a local file inside the
container,eg, _examples/settings.yml_.

The default image command will launch the gateway client with the settings
present under _/home/wirepas/vars/settings.yml_ (container path).

To run it with docker type

```shell
    docker run -it \
               -v $(pwd)/examples/settings.yml:/home/wirepas/backend-client/vars/settings.yml \
               --net=host \
               wirepas/backend-client \
               wm-gw-cli \
               --settings /home/wirepas/backend-client/vars/settings.yml \
               --debug_level=critical
```

:warning: **WARNING** :warning:

If you want to run against a MQTT running in your host (localhost),
you must overlay the container over your host's network.
To do so, you must set the docker run parameter _--net=host._

### Running with compose

To run the Backend Client using docker compose, drop or move the settings
file in **container/examples/settings.yml** and start the service with:

```shell
    docker-compose container/docker-compose.yml up
```

By default this will start the [MQTT viewer example][examples_mqtt_viewer].

If you wish to run the gateway command client you can do so with:

```shell
    docker-compose -f container/docker-compose.yml \
                   run \
                   backend-client wm-gw-cli \
                   --settings /home/wirepas/backend-client/vars/settings.yml
```

If you prefer alpine based images, please change _slim_ to _alpine_.

### Building the image locally

To build the image locally in the root of the repo type:

```shell
    docker build -f container/slim/Dockerfile -t backend-client .
```

Alternatively you can also build using the docker-compose.yml present in
the root of the directory:

```shell
    docker-compose -f container/docker-compose.yml  build
```

## Source documentation

The source documentation is found from
[read the docs.][backend_client_rtd]

## Contributing

We welcome your contributions!

Please read the [instructions on how to do it][here_contribution]
and please review our [code of conduct][here_code_of_conduct].

## License

Copyright 2019 Wirepas Ltd licensed under Apache License,
Version 2.0 See file [LICENSE][here_license] for full license details.

<!--- references --->

[bcli_api]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api

[bcli_management]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/management

[bcli_mesh]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/mesh

[bcli_messages]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/messages

[bcli_test]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/test

[bcli_tools]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/tools

[bcli_cli]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/cli.py

[bcli_api_influx]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api/influx

[bcli_api_mqtt]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api/mqtt

[bcli_api_mysql]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api/mysql

[bcli_api_wnt]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api/wnt

[bcli_api_wpe]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/api/wpe

[bcli_mesh_interfaces]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/mesh/interfaces

[bcli_mesh_interfaces_mqtt]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/mesh/interfaces/mqtt.py

[bcli_mesh_interfaces_remote_api]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/mesh/interfaces/remote_api.py

[bcli_mesh_interfaces_beacon_api]: https://github.com/wirepas/backend-client/tree/master/wirepas_backend_client/mesh/interfaces/beacon_api.py

[examples]: https://github.com/wirepas/backend-client/tree/master/examples

[examples_mqtt_viewer]: https://github.com/wirepas/backend-client/blob/master/examples/mqtt_viewer.py

[examples_find_all_nodes]: https://github.com/wirepas/backend-client/blob/master/examples/find_all_nodes.py

[examples_influx_viewer]: https://github.com/wirepas/backend-client/blob/master/examples/influx_viewer.py

[example_settings]: https://github.com/wirepas/backend-client/blob/master/examples/settings.yml

[example_provisioning]: https://github.com/wirepas/backend-client/blob/master/examples/provisioning_config.yml

[kpi_adv]: https://github.com/wirepas/backend-client/blob/master/wirepas_backend_client/test/kpi_adv.py

[wm_gw_cli]: https://github.com/wirepas/backend-client/blob/master/wirepas_backend_client/cli.py

[wm_wnt]: https://github.com/wirepas/backend-client/blob/master/wirepas_backend_client/api/wnt/__main__.py

[wm_wpe]: https://github.com/wirepas/backend-client/blob/master/wirepas_backend_client/api/wpe/__main__.py

[provisioning_server]: https://github.com/wirepas/backend-client/blob/master/wirepas_backend_client/provisioning/provisioning_server.py

[backend_client_dockerhub]: https://hub.docker.com/r/wirepas/backend-client

[backend_client_pypi]: https://pypi.org/project/wirepas-backend-client/

[backend_client_rtd]: https://backend-client.readthedocs.io/en/latest/

[backend_client_gh_issues]: https://github.com/wirepas/backend-client/issues

[backend_client_gh_releases]: https://github.com/wirepas/backend-client/releases

[backend_client_gh_milestones]: https://github.com/wirepas/backend-client/milestones

[backend_client_gh_projects]: https://github.com/wirepas/backend-client/projects

[here_img_overview]: https://github.com/wirepas/backend-client/blob/master/img/wm-backend-client-overview.png?raw=true

[here_container]: https://github.com/wirepas/backend-client/tree/master/container

[here_contribution]: https://github.com/wirepas/backend-client/blob/master/CONTRIBUTING.md

[here_code_of_conduct]: https://github.com/wirepas/backend-client/blob/master/CODE_OF_CONDUCT.md

[here_license]: https://github.com/wirepas/backend-client/blob/master/LICENSE

[here_setup_entrypoints]: https://github.com/wirepas/backend-client/blob/d18adb2e7927f1d19bee1d739964072fcb737889/setup.py#L84

[wirepas_cookbook_viz]: https://github.com/wirepas/tutorials/blob/master/cookbook/visualizations.md

[wirepas_gateway]: https://github.com/wirepas/gateway

[pipenv]: https://docs.pipenv.org/en/latest/

[virtualenv]: https://virtualenv.pypa.io/en/latest/

[docker]: https://www.docker.com
