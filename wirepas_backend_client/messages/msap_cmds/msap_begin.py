import struct

cmdMsapBeginReq: bytes = bytes([0x01])
cmdMsapBeginResp: bytes = bytes([0x81])


class MsapBeginReq:
    """ Command MSAP Begin request """

    __is_valid: bool = False
    __countdown_sec: int = 0x00

    @staticmethod
    def getType() -> int:
        return int(cmdMsapBeginReq[0])

    def __init__(self):
        self.__is_valid = True

    def toBytes(self) -> bytes:
        ret: bytes
        if self.__is_valid:
            # WP-RM-117, V5.0.A
            ret: bytes = cmdMsapBeginReq + bytes([0])
        else:
            raise ValueError("Not valid parameter for OtapMsapUpdateReq")
        return ret

    def is_valid(self) -> bool:
        return self.__is_valid


class MsapBeginResp:
    """ Command MSAP Begin request response """

    __is_valid: bool = False

    @staticmethod
    def getType() -> int:
        return int(cmdMsapBeginResp[0])

    def __init__(self, data_bytes):
        # Validate response type
        fmt = "=cc"  # if there is error message this does not pack rest

        if len(data_bytes) == struct.calcsize(fmt):
            message_len: int = data_bytes[1]
            # See WP-RM-117 @ MSAP Scratchpad Update
            # https://docs.python.org/3/library/struct.html?highlight=struct#format-characters

            if message_len == 0:
                fields = struct.unpack(fmt, data_bytes)
                (self.type, self.msgLen) = fields

                if self.type == cmdMsapBeginResp:
                    self.__is_valid = True
                else:
                    print("error: Error response type is {}".format(self.type))
            else:
                print("Unknown message. Message len is", message_len)
        else:
            print("Deserialization failed. Data size:", len(data_bytes))

    def is_valid(self) -> bool:
        return self.__is_valid
