import datetime
import struct

cmdMsapPingReq: bytes = bytes([0x00])
cmdMsapPingResp: bytes = bytes([0x80])

max_ref_len: int = 16


class MsapPingReq:
    """ Command MSAP Ping request """

    __is_valid: bool = False
    __ref_bytes: bytes = bytes()

    @staticmethod
    def getType() -> int:
        return int(cmdMsapPingReq[0])

    def __init__(self):
        self.setReference(self.generateReference())
        self.__is_valid = True

    @staticmethod
    def generateReference() -> bytes:
        seconds_since_epoch: int = int(datetime.datetime.now().timestamp())
        ref: bytes = seconds_since_epoch.to_bytes(8, byteorder="little")
        return ref

    def setReference(self, ref_bytes: bytes) -> bool:
        ret: bool = False
        if 0 < len(ref_bytes) <= max_ref_len:
            self.__ref_bytes = ref_bytes
            ret = True
        else:
            print("Ping reference not valid:{}".format(ref_bytes))
        return ret

    def getReference(self) -> bytes:
        return self.__ref_bytes

    def toBytes(self) -> bytes:
        ret: bytes
        if self.__is_valid:
            # WP-RM-117, V5.0.A
            ret: bytes = cmdMsapPingReq + bytes(
                [len(self.getReference())]
            ) + self.getReference()
        else:
            raise ValueError("Not valid parameter for MsapPingReq")
        return ret

    def is_valid(self) -> bool:
        ret: bool = False
        if 0 < len(self.__ref_bytes) <= max_ref_len:
            ret = True

        return ret


class MsapPingResp:
    """ Command MSAP Ping request response """

    __is_valid: bool = False
    __ref_bytes: bytes = bytes()

    @staticmethod
    def getType() -> int:
        return int(cmdMsapPingResp[0])

    def __init__(self, data_bytes):
        # Validate response type
        fmt = "=cc"  # if there is error message this does not pack rest

        if len(data_bytes) >= struct.calcsize(fmt):
            message_len: int = data_bytes[1]
            # See WP-RM-117 @ MSAP Scratchpad Ping
            # https://docs.python.org/3/library/struct.html
            # ?highlight=struct#format-characters

            header: bytes = data_bytes[0:2]

            fields = struct.unpack(fmt, header)
            (self.type, self.msgLen) = fields

            if self.type == cmdMsapPingResp:
                if len(data_bytes[2:]) == message_len:
                    self.__ref_bytes = data_bytes[2:]
                    self.__is_valid = True
                else:
                    print("error: payload len!=payload size")
                    self.__is_valid = False
            else:
                print("error: Error response type is {}".format(self.type))

        else:
            print("Deserialization failed. Data size:", len(data_bytes))

    def getReference(self) -> bytes:
        return self.__ref_bytes

    def is_valid(self) -> bool:
        return self.__is_valid
