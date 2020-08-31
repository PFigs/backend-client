import struct

cmdOtapMsapScratchpadUpdateReq: bytes = bytes([0x1A])
cmdOtapMsapScratchpadUpdateResp: bytes = bytes([0x9A])
cmdErrorInvalidBeginResp: bytes = bytes([0xFB])  # Error: Invalid begin


class MsapScratchpadUpdateReq:
    """ Command MSAP Scratchpad Update request """

    __is_valid: bool = False
    __scr_seq: int = 0x00

    @staticmethod
    def getType() -> int:
        return int(cmdOtapMsapScratchpadUpdateReq[0])

    def __init__(self):
        pass

    def setScrSequence(self, seq: int) -> bool:
        ret: bool = False
        min_seq: int = 0  # OTAP spec
        max_seq: int = 255  # OTAP spec

        if min_seq < seq <= max_seq:
            self.__is_valid = True
            self.__scr_seq = seq
            ret = True
        else:
            self.__is_valid = False

        return ret

    def toBytes(self) -> bytes:
        ret: bytes
        if self.__is_valid:
            # WP-RM-117, V5.0.A
            ret: bytes = cmdOtapMsapScratchpadUpdateReq + bytes(
                [0x01, self.__scr_seq]
            )
        else:
            raise ValueError("Not valid parameter for OtapMsapUpdateReq")
        return ret

    def is_valid(self) -> bool:
        return self.__is_valid


class MsapScratchpadUpdateResp:
    """ Command MSAP Scratchpad Update request response """

    __is_valid: bool = False

    @staticmethod
    def getType() -> int:
        return int(cmdOtapMsapScratchpadUpdateResp[0])

    def __init__(self, data_bytes):
        # Validate response type
        fmt = "=ccc"

        if len(data_bytes) == struct.calcsize(fmt):
            message_len: int = data_bytes[1]
            # See WP-RM-117 @ MSAP Scratchpad Update

            if message_len == 1:
                fields = struct.unpack(fmt, data_bytes)
                (self.type, self.msgLen, self.scrSequence) = fields

                if self.type == cmdOtapMsapScratchpadUpdateResp:
                    self.__is_valid = True
                elif self.type == cmdErrorInvalidBeginResp:
                    print(
                        "error: Error response type is "
                        "cmdErrorInvalidBeginResp"
                    )
                else:
                    print("error: Error response type is {}".format(self.type))
            else:
                print("Unknown message. Message len is", message_len)
        else:
            print("Deserialization failed. Data size:", len(data_bytes))

    def is_valid(self) -> bool:
        return self.__is_valid
