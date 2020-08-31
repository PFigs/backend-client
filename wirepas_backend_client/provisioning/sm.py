"""
    Provisioning state machine
    ==========================

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import queue
import logging
import threading
import enum
import datetime
import random

from Crypto.Hash import CMAC
from Crypto.Cipher import AES
from Crypto.Util import Counter

from wirepas_messaging.gateway.api import GatewayResultCode
from wirepas_backend_client.provisioning.events import ProvisioningEventTimeout
from wirepas_backend_client.provisioning.message import (
    ProvisioningMessageDATA,
    ProvisioningMessageNACK,
    ProvisioningMessageTypes,
    ProvisioningNackReason,
    ProvisioningMethod,
)

from wirepas_backend_client.api import Topics


class ProvisioningStates(enum.Enum):
    """ Provisioning states """

    IDLE = 0
    WAIT_DATA_SENT = 1
    WAIT_RESPONSE = 2
    WAIT_NACK_SENT = 3


class ProvisioningStatus(enum.Enum):
    """ Provisioning status """

    ONGOING = 0
    SUCCESS = 1
    FAILURE = 2
    ERROR_NO_ACK = 3
    ERROR_SENDING_DATA = 4
    ERROR_SENDING_NACK = 5
    ERROR_NOT_AUTHORIZED = 6
    ERROR_NOT_START = 7
    ERROR_INVALID_STATE = 8
    ERROR_NACK_RECEIVED = 9
    ERROR_NO_RESPONSE = 10


class ProvisioningStateMachine(object):
    def __init__(
        self,
        server,
        sm_id,
        data,
        retry=1,
        timeout=180,
        exit_signal=None,
        logger=None,
    ):
        super(ProvisioningStateMachine, self).__init__()

        self.server = server
        self.sm_id = sm_id
        self.data = data
        self.retry = retry
        self.timeout = timeout
        self.exit_signal = exit_signal

        self.logger = logger or logging.getLogger(__name__)

        self.mqtt_topics = Topics()
        self.event_q = queue.Queue()

        self.counter = random.getrandbits(16)

        self.state = ProvisioningStates.IDLE
        self.status = ProvisioningStatus.ONGOING
        self._data_pkt = None
        self._timer = None

        self.sink_id = None
        self.gw_id = None
        self._tx_time = datetime.datetime(
            year=datetime.MINYEAR, month=1, day=1, tzinfo=datetime.timezone.utc
        )

        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def __str__(self):
        return "".join(
            [
                "[{:08X}".format(self.sm_id[0]),
                ", ",
                "".join("{:02X}".format(x) for x in self.sm_id[1]),
                ", {:02X}".format(self.sm_id[2]),
                "]",
            ]
        )

    def _timeout(self):
        self.event_q.put(ProvisioningEventTimeout())

    def _update_origin(self, msg):
        if self._tx_time < msg.tx_time:
            self.sink_id = msg.sink_id
            self.gw_id = msg.gw_id
            self._tx_time = msg.tx_time

    def _timer_start(self, timeout):
        if self._timer is not None:
            self._timer_cancel()
        self._timer = threading.Timer(self.timeout, self._timeout)
        self._timer.start()

    def _timer_cancel(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer.join()
            self._timer = None

    def _send_packet(self, payload):
        message = self.mqtt_topics.request_message(
            "send_data",
            **dict(
                sink_id=self.sink_id,
                gw_id=self.gw_id,
                dest_add=self.sm_id[0],
                src_ep=255,
                dst_ep=246,
                qos=1,
                payload=payload,
            )
        )
        self.server.send_packet(self, message)

    def _encrypt_packet(self, uid, iv, plain_text):
        enc_key = self.data[uid]["factory_key"][16:32]
        auth_key = self.data[uid]["factory_key"][0:16]

        self.logger.info("  - Encrypt DATA packet")
        # Increment counter
        self.counter += 1
        self.logger.debug(
            "   -  IV: %s", "".join("{:02X}".format(x) + " " for x in iv)
        )
        self.logger.debug("   - Counter : %s", str(self.counter))

        # Authenticate Header + Payload
        to_auth = ProvisioningMessageDATA(
            self.sm_id[1], self.sm_id[2], self.counter, plain_text
        ).payload

        # Create a CMAC / OMAC1 object.
        cobj = CMAC.new(auth_key, ciphermod=AES)
        cobj.update(to_auth)

        # MIC is 5 first bytes
        mic = cobj.digest()[0:5]

        # Encrypt payload + mic
        # Generate Initial Counter Block (ICB).
        ctr_bytes = self.counter + int.from_bytes(
            iv, byteorder="little", signed=False
        )

        ctr_bytes = ctr_bytes % (2 ** 128)
        icb = ctr_bytes.to_bytes(16, byteorder="little")

        self.logger.debug(
            "   -  ICB: %s", "".join("{:02X}".format(x) + " " for x in icb)
        )

        # Create an AES Counter (CTR) mode cipher using ICB.
        ctr = Counter.new(
            128,
            little_endian=True,
            allow_wraparound=True,
            initial_value=int.from_bytes(
                icb, byteorder="little", signed=False
            ),
        )
        cipher = AES.new(enc_key, AES.MODE_CTR, counter=ctr)
        plain_text += mic
        plain_text = bytes(cipher.encrypt(plain_text))

        return plain_text

    def _process_start(self, msg):
        # This is a START packet

        if (
            msg.uid in self.data.keys()
            and self.data[msg.uid]["method"] == msg.method
        ):
            self.logger.info(
                "  - Sending Provisioning DATA for UID(%s).", msg.uid
            )

            data_bytes = self.data.getCbor(msg.uid)

            if msg.method == ProvisioningMethod.UNSECURED:
                key_idx = 0
            else:
                key_idx = 1
                data_bytes = self._encrypt_packet(msg.uid, msg.iv, data_bytes)

            self._data_pkt = ProvisioningMessageDATA(
                self.sm_id[1],
                self.sm_id[2],
                self.counter,
                data_bytes,
                key_index=key_idx,
            ).payload
            self.logger.debug(
                " - Provisioning DATA packet: %s",
                "".join("{:02X}".format(x) + " " for x in self._data_pkt),
            )
            self._send_packet(self._data_pkt)
            self._timer_start(self.timeout)
            self.state = ProvisioningStates.WAIT_DATA_SENT
        else:
            self.status = ProvisioningStatus.ERROR_NOT_AUTHORIZED

            if msg.uid not in self.data.keys():
                reason = ProvisioningNackReason.NOT_AUTHORIZED
            else:
                reason = ProvisioningNackReason.METHOD_NOT_SUPPORTED

            self.logger.error(
                " - UID(%s) not in whitelist"
                " (or method not supported) - Send NACK (%s).",
                msg.uid,
                reason,
            )
            self._send_packet(
                ProvisioningMessageNACK(
                    self.sm_id[1], self.sm_id[2], reason
                ).payload
            )
            self._timer_start(self.timeout)
            self.state = ProvisioningStates.WAIT_NACK_SENT

    def _process_error_data(self, msg):
        self.retry -= 1
        if self.retry >= 0:
            self.logger.warning("  - %s - Re-send DATA.", msg)
            self._send_packet(self._data_pkt)
            self._timer_start(self.timeout)
            self.state = ProvisioningStates.WAIT_DATA_SENT
        else:
            self.logger.error(
                "  - %s - Too many retry - Provisioning FAILURE.", msg
            )
            self._timer_cancel()
            self.status = ProvisioningStatus.ERROR_SENDING_DATA

    def _state_idle(self, event):
        self.logger.info("%s State IDLE:", str(self))

        if (
            event.type == "packet_rxd"
            and event.msg.msg_type == ProvisioningMessageTypes.START
        ):
            self.logger.info("  - Received START packet.")
            self._update_origin(event.msg)
            self._process_start(event.msg)
        else:
            self.logger.error(
                "  - Received packet is not a START packet"
                " - Provisioning FAILURE."
            )
            self._timer_cancel()
            self.status = ProvisioningStatus.ERROR_NOT_START

    def _state_wait_data_sent(self, event):
        self.logger.info("%s State Wait Data Sent:", str(self))

        if event.type == "packet_sent":
            if event.res == GatewayResultCode.GW_RES_OK:
                self.logger.info("  - DATA packet sent.")
                self.state = ProvisioningStates.WAIT_RESPONSE
                self._timer_start(self.timeout)
            else:
                self._process_error_data("Error sending DATA ({event.res})")

        elif event.type == "timeout":
            self._process_error_data("Timeout sending DATA")

    def _state_wait_response(self, event):
        self.logger.info("%s State Wait Node Response:", str(self))

        if event.type == "packet_rxd":
            self._update_origin(event.msg)
            if event.msg.msg_type == ProvisioningMessageTypes.START:
                self.logger.warning(
                    "  - START packet (re)received" " - Re-send DATA."
                )
                self._process_start(event.msg)
                self._timer_start(self.timeout)
                self.state = ProvisioningStates.WAIT_DATA_SENT

            elif event.msg.msg_type == ProvisioningMessageTypes.DATA_ACK:
                self.logger.info("  - ACK received, Provisioning SUCCESS.")
                self._timer_cancel()
                self.status = ProvisioningStatus.SUCCESS

            elif event.msg.msg_type == ProvisioningMessageTypes.NACK:
                self.logger.info(
                    "  - NACK received (%s)," " Provisioning FAILURE.",
                    event.msg.reason,
                )
                self._timer_cancel()
                self.status = ProvisioningStatus.ERROR_NACK_RECEIVED
        elif event.type == "timeout":
            self.logger.error(
                "  - No response from Node, Provisioning FAILURE."
            )
            self._timer_cancel()
            self.status = ProvisioningStatus.ERROR_NO_RESPONSE

    def _state_wait_nack_sent(self, event):
        self.logger.info("%s State Wait NACK Sent:", str(self))

        if event.type == "timeout":
            self.logger.error(
                "  - timeout sending NACK, Provisioning FAILURE."
            )
            self.status = ProvisioningStatus.ERROR_SENDING_NACK

        elif event.type == "packet_sent":
            if event.res == GatewayResultCode.GW_RES_OK:
                self.logger.info(
                    "  - NACK sent successfully, Provisioning FAILURE."
                )
                self.status = ProvisioningStatus.ERROR_NOT_AUTHORIZED
                self._timer.cancel()
            else:
                self.retry -= 1
                if self.retry >= 0:
                    self.logger.warning(
                        "  - Error sending NACK - Re-send NACK."
                    )
                    self._send_packet(
                        ProvisioningMessageNACK(
                            self.sm_id[1],
                            self.sm_id[2],
                            ProvisioningNackReason.NOT_AUTHORIZED,
                        ).payload
                    )
                    self._timer_start(self.timeout)
                    self.state = ProvisioningStates.WAIT_NACK_SENT
                else:
                    self.logger.error(
                        "  - Error sending NACK - Too many retry"
                        " - Provisioning FAILURE."
                    )
                    self._timer.cancel()
                    self.status = ProvisioningStatus.ERROR_SENDING_NACK

    def run(self):

        while (
            not self.exit_signal.is_set()
            and self.status == ProvisioningStatus.ONGOING
        ):
            try:
                event = self.event_q.get(block=True, timeout=100)
            except queue.Empty:
                self.logger.debug("%s Queue empty", str(self))
                continue

            self.logger.debug("%s Event : %s", str(self), event.type)

            # IDLE
            if self.state == ProvisioningStates.IDLE:
                self._state_idle(event)

            # WAIT DATA SENT
            elif self.state == ProvisioningStates.WAIT_DATA_SENT:
                self._state_wait_data_sent(event)

            # WAIT NODE RESPONSE
            elif self.state == ProvisioningStates.WAIT_RESPONSE:
                self._state_wait_response(event)

            # WAIT NACK SENT
            elif self.state == ProvisioningStates.WAIT_NACK_SENT:
                self._state_wait_nack_sent(event)

            else:
                self.logger.error(
                    "%s Invalid state - Provisioning FAILURE.", str(self)
                )
                self.status = ProvisioningStatus.ERROR_INVALID_STATE
