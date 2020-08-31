from enum import Enum
from struct import pack
import binascii


class SetDiagnosticsIntervals(Enum):
    intervalOff = 0
    i30 = 30
    i60 = 60
    i120 = 120
    i300 = 300
    i600 = 600
    i1200 = 1200


class DiagnosticsMinimalContent(Enum):
    NodeDiagnostics = 0x01
    NeighBorDiagnostics = 0x02
    ScanDiagnostics = 0x03
    BootInfoDiagnostics = 0x04  # Always enabled
    DisableAllDiagV2 = 0xFF


class DiagnosticsRequestTypes(Enum):
    DiagnosticControlRequest = 0x60


class DiagnosticsResponseTypes(Enum):
    DiagnosticControlResponse = 0x60 | 0x80


class SendToSinkOnly(Enum):
    no = 0
    yes = 1


class ControlMessage:
    def __init__(
        self,
        gatewayId,
        sinkId,
        nodeDestinationAddress,
        destinationEndPoint,
        sourceEndPoint,
        payload,
    ):
        self._gatewayId = gatewayId
        self._sinkId = sinkId
        self._nodeDestinationAddress = nodeDestinationAddress
        self._destinationEndPoint = destinationEndPoint
        self._sourceEndPoint = sourceEndPoint
        self._payload = payload

    def __str__(self):
        return "{:2}/{:2} sEndPoint:{:3} dEndPoint: {:3} dAddress: {:10} payload: {}".format(
            self._gatewayId,
            self._sinkId,
            self._sourceEndPoint,
            self._destinationEndPoint,
            self._nodeDestinationAddress,
            binascii.hexlify(self._payload),
        )

    @property
    def nodeDestinationAddress(self):
        return self._nodeDestinationAddress

    @property
    def sinkId(self):
        return self._sinkId

    @property
    def gatewayId(self):
        return self._gatewayId

    @property
    def destinationEndPoint(self):
        return self._destinationEndPoint

    @property
    def sourceEndPoint(self):
        return self._sourceEndPoint

    @property
    def payload(self):
        return self._payload


class DiagnosticControlMessageBuilder:
    def __init__(self):
        self._addressBroadcast = 4294967295
        self._thisSourceEndPoint = 255
        self._defaultDiagnosticControlEndPoint = 240

    def buildSetNeighborDiagnostics(
        self,
        targetGatewayId: object,
        targetSinkId: object,
        targetSinkAddress: int,
        interval: SetDiagnosticsIntervals,
        sentToSinkOnly: SendToSinkOnly,
    ) -> ControlMessage:
        payload: bytes

        # https://docs.python.org/3/library/struct.html

        typeFmt = ">B"
        minimalContentFmt = "<B"
        intervalPackedFmt = "<H"
        lengthPackedFmt = ">B"

        typePacked: bytes = pack(
            typeFmt, DiagnosticsRequestTypes.DiagnosticControlRequest.value
        )
        intervalPacked: bytes = pack(intervalPackedFmt, interval)

        if SetDiagnosticsIntervals.intervalOff.value == interval:
            minimalContent: bytes = pack(
                minimalContentFmt,
                DiagnosticsMinimalContent.DisableAllDiagV2.value,
            )
        else:
            minimalContent: bytes = pack(
                minimalContentFmt,
                DiagnosticsMinimalContent.NeighBorDiagnostics.value,
            )

        lengthPacked: bytes = pack(
            lengthPackedFmt, len(intervalPacked) + len(minimalContent)
        )

        payload = typePacked + lengthPacked + intervalPacked + minimalContent

        msg = None
        if sentToSinkOnly == sentToSinkOnly.yes:
            msg = ControlMessage(
                targetGatewayId,
                targetSinkId,
                targetSinkAddress,
                self._defaultDiagnosticControlEndPoint,
                self._thisSourceEndPoint,
                payload,
            )
        else:
            msg = ControlMessage(
                targetGatewayId,
                targetSinkId,
                self._addressBroadcast,
                self._defaultDiagnosticControlEndPoint,
                self._thisSourceEndPoint,
                payload,
            )
        return msg

    def buildPing(
        self, targetGatewayId: object, targetSinkId: object
    ) -> object:
        payload = bytes.fromhex("0000")
        msg = ControlMessage(
            targetGatewayId,
            targetSinkId,
            self._addressBroadcast,
            self._defaultDiagnosticControlEndPoint,
            self._thisSourceEndPoint,
            payload,
        )
        return msg
