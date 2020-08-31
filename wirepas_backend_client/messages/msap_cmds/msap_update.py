import struct

msap_update_msg_len = 2
cmdMsapUpdateReq: bytes = bytes([0x05])
cmdMsapUpdateResp: bytes = bytes([0x85])
cmdErrorInvalidBeginResp: bytes = bytes([0xFB])  # Error: Invalid begin


class MsapUpdateReq:
    """ Command MSAP Update request """

    __is_valid: bool = False
    __countdown_sec: int = 0x00

    @staticmethod
    def getType() -> int:
        return int(cmdMsapUpdateReq[0])

    def __init__(self):
        pass

    def setCountDown(self, seq: int) -> bool:
        ret: bool = False
        min_val: int = 10  # MSAP update
        max_val: int = 32767  # MSAP update

        if min_val <= seq <= max_val:
            self.__is_valid = True
            self.__countdown_sec = seq
            ret = True
        else:
            self.__is_valid = False

        return ret

    def toBytes(self) -> bytes:
        ret: bytes
        if self.__is_valid:
            # WP-RM-117, V5.0.A
            timeLenBytes: int = 2
            ret: bytes = cmdMsapUpdateReq + bytes(
                [timeLenBytes]
            ) + self.__countdown_sec.to_bytes(timeLenBytes, byteorder="little")
        else:
            raise ValueError("Not valid parameter for OtapMsapUpdateReq")
        return ret

    def is_valid(self) -> bool:
        return self.__is_valid


class MsapUpdateResp:
    """ Command MSAP Update request response """

    __is_valid: bool = False

    @staticmethod
    def getType() -> int:
        return int(cmdMsapUpdateResp[0])

    def __init__(self, data_bytes):
        # Validate response type
        fmt = "=ccH"  # if there is error message this does not pack rest

        if len(data_bytes) == struct.calcsize(fmt):
            message_len: int = data_bytes[1]
            # See WP-RM-117 @ MSAP Scratchpad Update
            # https://docs.python.org/3/library/struct.html?highlight=struct#format-characters

            if message_len == msap_update_msg_len:
                fields = struct.unpack(fmt, data_bytes)
                (self.type, self.msgLen, self.time) = fields  # LSB, MSB

                if self.type == cmdMsapUpdateResp:
                    self.__is_valid = True
                elif self.type == cmdErrorInvalidBeginResp:
                    print("error: Invalid begin (countdown running?)")
                    pass
                else:
                    print("error: Error response type is {}".format(self.type))
            else:
                print("Unknown message. Message len is", message_len)
        else:
            print("Deserialization failed. Data size:", len(data_bytes))

    def is_valid(self) -> bool:
        return self.__is_valid
