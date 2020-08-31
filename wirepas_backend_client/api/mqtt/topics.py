"""
    Topics
    ======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import wirepas_messaging


class Topics(object):
    """
    MQTT Topics

    An helper class to manage the API MQTT topics.

    All topics are inside a dictionary,

    requests
    responses
    events

    The first element of the dictionary is the version number.

    """

    def __init__(self, api_version: str = "1"):
        super(Topics, self).__init__()
        if api_version != "1":
            raise ValueError("Unsupported API version")

        self.api_version = str(api_version)
        self._topics = dict()
        self._build_topics(str(api_version))

        self._default_attributes = dict(
            gw_id="+", sink_id="+", network_id="+", src_ep="+", dst_ep="+"
        )

    def list(self):
        """ Provides a dictionary with a list of known requests,
            events and response topics
        """
        return dict(
            requests=self._topics[self.api_version]["request"].values(),
            events=self._topics[self.api_version]["event"].values(),
            responses=self._topics[self.api_version]["request"].values(),
        )

    def _build_topics(self, api_version: str = "1"):
        """ Builds the internal dictionary with topics based on the input arguments """

        self._topics = {
            api_version: dict(request=dict(), response=dict(), event=dict())
        }

        # Requests
        self._topics[api_version]["request"]["get_configs"] = dict(
            path="gw-request/get_configs/{gw_id}",
            constructor=wirepas_messaging.gateway.api.GetConfigsRequest,
        )

        self._topics[api_version]["request"]["set_config"] = dict(
            path="gw-request/set_config/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SetConfigRequest,
        )

        self._topics[api_version]["request"]["send_data"] = dict(
            path="gw-request/send_data/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SendDataRequest,
        )

        self._topics[api_version]["request"]["otap_status"] = dict(
            path="gw-request/otap_status/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.GetScratchpadStatusRequest,
        )

        self._topics[api_version]["request"]["otap_load_scratchpad"] = dict(
            path="gw-request/otap_load_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.UploadScratchpadRequest,
        )

        self._topics[api_version]["request"]["otap_process_scratchpad"] = dict(
            path="gw-request/otap_process_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.ProcessScratchpadRequest,
        )

        # Responses
        self._topics[api_version]["response"]["get_configs"] = dict(
            path="gw-response/get_configs/{gw_id}",
            constructor=wirepas_messaging.gateway.api.GetConfigsResponse,
        )

        self._topics[api_version]["response"]["set_config"] = dict(
            path="gw-response/set_config/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SetConfigResponse,
        )

        self._topics[api_version]["response"]["send_data"] = dict(
            path="gw-response/send_data/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SendDataResponse,
        )

        self._topics[api_version]["response"]["otap_status"] = dict(
            path="gw-response/otap_status/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.GetScratchpadStatusResponse,
        )

        self._topics[api_version]["response"]["otap_load_scratchpad"] = dict(
            path="gw-response/otap_load_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.UploadScratchpadResponse,
        )

        self._topics[api_version]["response"][
            "otap_process_scratchpad"
        ] = dict(
            path="gw-response/otap_process_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.ProcessScratchpadResponse,
        )

        # Asynchronous events
        self._topics[api_version]["event"]["clear"] = dict(
            path="gw-event/status/{gw_id}",
            constructor=wirepas_messaging.gateway.GenericMessage,
        )

        self._topics[api_version]["event"]["status"] = dict(
            path="gw-event/status/{gw_id}",
            constructor=wirepas_messaging.gateway.api.StatusEvent,
        )

        self._topics[api_version]["event"]["received_data"] = dict(
            path="gw-event/received_data/{gw_id}/{sink_id}/{network_id}/{src_ep}/{dst_ep}",
            constructor=wirepas_messaging.gateway.api.ReceivedDataEvent,
        )

        # Generic fallback
        self._topics[api_version]["event"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Event
        )
        self._topics[api_version]["request"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Request
        )
        self._topics[api_version]["response"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Response
        )

    def request(self, name, **kwargs):
        """ returns a string for the request identified by name """
        return self.path(topic_type="request", name=name, **kwargs)

    def response(self, name, **kwargs):
        """ returns a string for the response identified by name """
        return self.path(topic_type="response", name=name, **kwargs)

    def event(self, name, **kwargs):
        """ returns a string for the event identified by name """
        return self.path(topic_type="event", name=name, **kwargs)

    def request_message(self, name, **kwargs):
        """ constructs a request message for the topic identified by name """
        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["request"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                message = dict(
                    topic=path, data=topic_info["constructor"](**kwargs)
                )
        return message

    def response_message(self, name, **kwargs):
        """ constructs a response message for the topic identified by name """
        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["response"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                message = dict(
                    topic=path, data=topic_info["constructor"](**kwargs)
                )
        return message

    def event_message(self, name, **kwargs):
        """ constructs an event message for the topic identified by name """

        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["event"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                message = dict(
                    topic=path, data=topic_info["constructor"](**kwargs)
                )

        return message

    def path(self, topic_type: str, name: str, **kwargs):
        """
        Builds a topic based on its type, name and kwargs

        Args:
            topic_type: request/response/envent
            name: which request/response/event to build
            kwargs: expects a keyword list with:
                        gateway_id
                        sink_id
                        network_id
                        source_endpoint
                        destination_endpoint

        If no kwargs are provided, the gw_id and sink_id are set to '+'.
        """
        topic_type = topic_type.lower()
        name = name.lower()

        if topic_type not in self._topics[self.api_version]:
            return None

        topic = self._topics[self.api_version][topic_type][name]
        if kwargs:
            topic = topic["path"].format(**kwargs)
        else:
            topic = topic["path"].format(**self._default_attributes)

        return topic

    def constructor(self, topic_type: str, name: str):
        """ retrieves the message that is in use for a given topic """

        topic_type = topic_type.lower()
        name = name.lower()

        if topic_type not in self._topics[self.api_version]:
            return None

        constructor = self._topics[self.api_version][topic_type][name][
            "constructor"
        ]

        if constructor is None:
            constructor = self._topics[self.api_version][topic_type][
                "generic"
            ]["constructor"]

        return constructor
