from time import sleep
from time import time
from datetime import datetime

# multiple definitions exists
from wirepas_backend_client.api.mqtt import Topics
from wirepas_messaging.gateway.api import GatewayResultCode
from wirepas_backend_client.mesh.state import MeshManagement

from wirepas_backend_client.mesh.set_diagnostics.fea_set_neighbor_diagnostic_message_builder import (
    ControlMessage,
    DiagnosticControlMessageBuilder,
    SetDiagnosticsIntervals,
    SendToSinkOnly,
)


class DiagnosticActivationStatus:
    def __init__(self, requestId, gatewayId, sinkId, nodeDestinationAddress):
        self.gatewayId = gatewayId
        self.sinkId = sinkId
        self.requestId = requestId
        self.responseReceived = False
        self.receivedResponseWasOk = False
        self.nodeDestinationAddress = nodeDestinationAddress


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class DuplicateReqId(Error):
    def __init__(self, message):
        self.message = message


class SetDiagnostics:
    def __init__(self, deviceManager: MeshManagement):
        self._processingActive: bool = True
        self._networkIdToUse: int = 0
        self._diagnosticIntervalSecs: SetDiagnosticsIntervals = SetDiagnosticsIntervals.intervalOff
        self._deviceManager: MeshManagement = deviceManager
        self._mqttSendFn = None
        self._diagnosticActivationStatuses = dict()
        self.mqtt_topics = Topics()
        self._defaultPollTimeSec = 0.1
        self._operationStart = None
        self._sinksAddressInfo = None
        self._messageTxList = list()
        self._defaultOperationTimeOutSec = 30

    @staticmethod
    def _pollWaitSecond():
        sleep(1)

    @staticmethod
    def _amountOfNOkResponsesReceived(requestStat: dict):
        ret = 0
        for value in requestStat.values():
            if value.responseReceived is True:
                if value.receivedResponseWasOk is False:
                    ret = ret + 1
        return ret

    @staticmethod
    def _amountOfOkResponsesReceived(requestStat: dict):
        ret = 0
        for value in requestStat.values():
            if value.responseReceived is True:
                if value.receivedResponseWasOk is True:
                    ret = ret + 1
        return ret

    @staticmethod
    def _isAllResponsesReceived(requestStat: dict):
        ret = True
        for value in requestStat.values():
            if value.responseReceived is False:
                ret = False
                break
        return ret

    def _getNodeAddress(self, gatewayId, sinkId) -> int:
        ret = self._sinksAddressInfo[gatewayId][sinkId]
        return ret

    def _getElapsedTimeSting(self):
        end = time()
        elapsedSecs = end - self._operationStart
        ret = str(
            datetime.now().strftime("%H:%M.%S")
        ) + " ({0:3.1f} secs) ".format(elapsedSecs)
        return ret

    def _postControlMessage(self, msg: ControlMessage):
        f = self._mqttSendFn
        messageRequestId = f(
            msg.gatewayId,
            msg.sinkId,
            msg.nodeDestinationAddress,
            msg.destinationEndPoint,
            msg.sourceEndPoint,
            msg.payload,
        )
        ret = messageRequestId
        return ret

    def _reportProgress(self):
        totalReqs = len(self._diagnosticActivationStatuses)
        totalOk = self._amountOfOkResponsesReceived(
            self._diagnosticActivationStatuses
        )
        totalNok = self._amountOfNOkResponsesReceived(
            self._diagnosticActivationStatuses
        )

        print(
            "{0:16}: Progress {1:2} /{2:2} ({3:3.0f}%). Ok so far {4:3.0f}%."
            " Fails: {5:3.0f}%".format(
                self._getElapsedTimeSting(),
                (totalOk + totalNok),
                totalReqs,
                (totalOk + totalNok) / totalReqs * 100,
                totalOk / totalReqs * 100,
                totalNok / totalReqs * 100,
            )
        )

    def setArguments(
        self, networkId: int, diagnosticIntervalSecs: int
    ) -> bool:
        ret: bool = False
        if networkId > 0:
            self._networkIdToUse = networkId
            self._diagnosticIntervalSecs = diagnosticIntervalSecs
            ret = True

        return ret

    def abort(self):
        print("Requested abort")
        self._processingActive = False

    def _sendMessage(self, msg):
        messageRequestId = self._postControlMessage(msg)

        if messageRequestId not in self._diagnosticActivationStatuses:

            self._diagnosticActivationStatuses[
                messageRequestId
            ] = DiagnosticActivationStatus(
                messageRequestId,
                msg.gatewayId,
                msg.sinkId,
                msg.nodeDestinationAddress,
            )
        else:
            raise DuplicateReqId(
                "Duplicate request id '{}'".format(messageRequestId)
            )

    def performOperation(self) -> bool:

        operationResult: bool
        operationResult = False

        commandOkString = "Network diagnostic operation OK!"
        commandNokString = "Network diagnostic operation FAIL!"

        self._processingActive = True

        timeOutCounterSec = self._defaultOperationTimeOutSec

        if self._processingActive:

            self._operationStart = time()

            networkSinks: dict
            networkSinks = self.getSinksBelongingToNetwork(
                self._networkIdToUse
            )

            if networkSinks is not None:
                print(" ")
                # Post requests, store req id and start waiting responses
                for gatewayId in networkSinks.keys():
                    gwSinks = networkSinks.get(gatewayId)
                    for sinkId in gwSinks.keys():
                        builder = DiagnosticControlMessageBuilder()
                        controlMsgToBeBroadCasted: ControlMessage
                        controlMsgToBeBroadCasted = builder.buildSetNeighborDiagnostics(
                            gatewayId,
                            sinkId,
                            self._getNodeAddress(gatewayId, sinkId),
                            self._diagnosticIntervalSecs,
                            SendToSinkOnly.yes,
                        )

                        controlMsgToBeSentToSink: ControlMessage
                        controlMsgToBeSentToSink = builder.buildSetNeighborDiagnostics(
                            gatewayId,
                            sinkId,
                            self._getNodeAddress(gatewayId, sinkId),
                            self._diagnosticIntervalSecs,
                            SendToSinkOnly.no,
                        )

                        print(
                            "Build message to be sent :",
                            controlMsgToBeBroadCasted,
                        )
                        print(
                            "Build message to be sent :",
                            controlMsgToBeSentToSink,
                        )

                        self._messageTxList.append(controlMsgToBeBroadCasted)
                        self._messageTxList.append(controlMsgToBeSentToSink)

                print("")
                print("Start sending messages.")
                if len(self._messageTxList) > 0:
                    # send first message
                    self._sendMessage(self._messageTxList[0])
                    self._messageTxList.pop(0)

                print("")
                print("Progress:")
                self._reportProgress()

                while self._processingActive:
                    self._pollWaitSecond()
                    timeOutCounterSec = timeOutCounterSec - 1
                    if timeOutCounterSec == 0:
                        self._processingActive = False
                        if (
                            self._isAllResponsesReceived(
                                self._diagnosticActivationStatuses
                            )
                            is True
                            and self._amountOfNOkResponsesReceived(
                                self._diagnosticActivationStatuses
                            )
                            == 0
                        ):
                            print(" ")
                            print("Result:")
                            print("Network diagnostic operation successful!")
                            print(commandOkString)
                            operationResult = True
                        else:
                            print(" ")
                            print("Result:")
                            print(
                                "Error: Timeout and not all devices reported "
                                "ok. "
                            )
                            print(commandNokString)
                            operationResult = False
                    else:
                        if self._isAllResponsesReceived(
                            self._diagnosticActivationStatuses
                        ):
                            if (
                                self._amountOfNOkResponsesReceived(
                                    self._diagnosticActivationStatuses
                                )
                                == 0
                            ):
                                print(" ")
                                print("Result:")
                                print("All gateways involved reported ok")
                                print(commandOkString)
                                self._processingActive = False
                                operationResult = True
                            else:
                                print(" ")
                                print("Result:")
                                print(
                                    "Error: Not all gateways involved "
                                    "reported ok"
                                )
                                print(commandOkString)
                                self._processingActive = False
                                operationResult = False
                        else:
                            # keep waiting responses
                            pass
            else:
                print(" ")
                print("Result:")
                print("No devices belonging to network")
                print(commandNokString)
        else:
            print(" ")
            print("Result:")
            print("Error: Command arguments invalid")

        return operationResult

    def setSinksAddressInfo(self, sinksAddressInfo: dict):
        self._sinksAddressInfo = sinksAddressInfo

    def setMQTTmessageSendFunction(self, txFunc):
        self._mqttSendFn = txFunc

    def onDataQueueMessage(self, message):
        pass

    def onEventQueueMessage(self, message):
        pass

    def onResponseQueueMessage(self, message):

        if message.req_id in self._diagnosticActivationStatuses:
            # perform additional checking
            if (
                message.gw_id
                == self._diagnosticActivationStatuses[message.req_id].gatewayId
            ):
                if (
                    message.sink_id
                    == self._diagnosticActivationStatuses[
                        message.req_id
                    ].sinkId
                ):
                    self._diagnosticActivationStatuses[
                        message.req_id
                    ].responseReceived = True

                    if message.res == GatewayResultCode.GW_RES_OK:
                        self._diagnosticActivationStatuses[
                            message.req_id
                        ].receivedResponseWasOk = True
                    else:
                        self._diagnosticActivationStatuses[
                            message.req_id
                        ].receivedResponseWasOk = False

                    # send next message
                    if len(self._messageTxList) > 0:
                        self._sendMessage(self._messageTxList[0])
                        self._messageTxList.pop(0)

                    self._reportProgress()

    def getSinksBelongingToNetwork(self, networkId: int):
        ret = dict()
        sinks: dict
        sinks = self._deviceManager.sinks

        for sink in sinks:
            if int(sink.network_id) == int(networkId):
                gw_id = sink.gateway_id

                if gw_id not in ret:
                    ret[gw_id] = dict()

                ret[gw_id][sink.device_id] = sink

        if len(ret) == 0:
            ret = None

        return ret
