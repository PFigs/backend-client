import struct

cmdMSapScratchPadStatusReq: bytes = bytes([0x19])
cmdMSapScratchPadStatusResp: bytes = bytes([0x99])


class MsapScratchPadStatusReq:
    __is_valid: bool = False

    @staticmethod
    def getType() -> int:
        return int(cmdMSapScratchPadStatusReq[0])

    def __init__(self):
        pass

    def toBytes(self) -> bytes:
        ret: bytes = cmdMSapScratchPadStatusReq + bytes(
            [0x00]
        )  # WP-RM-117, V5.0.A
        return ret


class MsapScratchPadStatusResp:
    __is_valid: bool = False

    @staticmethod
    def getType() -> int:
        return int(cmdMSapScratchPadStatusResp[0])

    def __init__(self, data_bytes):
        message_len_short: int = 24  # WP-RM-117, V5.0.A
        message_len_long: int = 39  # WP-RM-117, V5.0.A

        min_message_len: int = message_len_short

        # Validate response type
        if len(data_bytes) >= min_message_len:
            message_len: int = data_bytes[1]  # [0] type #[1] len
            # Validate length WP-RM-117, V5.0.A

            # https://stackoverflow.com/questions/38829921/
            # use-struct-in-python-to-deserialize-a-byte-array-coming-from-serial

            if message_len == message_len_short:
                # Short path
                fmt = "=ccIHcccIHcIc"
                fields = struct.unpack(fmt, data_bytes)
                (
                    self.type,
                    self.msgLen,
                    self.storedScratchPadNumberOfBytes,
                    self.storedScratchPadCRC,
                    self.storedScratchSeq,
                    self.storedScratchType,
                    self.storedScratchStatus,
                    self.processedScratchPadNumberOfBytes,
                    self.processedScratchPadCRC,
                    self.processedScratchPadSeq,
                    self.processedFirmwareAreaId,
                    self.FWmajorVer,
                    self.FWminorVer,
                ) = fields

                self.__is_valid = True

            elif message_len == message_len_long:
                # Long path
                # https://docs.python.org/3/library/struct.html?highlight=struct#format-characters

                fmt = "=ccIHcccIHcIccccIHcIcccc"
                fields = struct.unpack(fmt, data_bytes)
                (
                    self.type,
                    self.msgLen,
                    self.storedScratchPadNumberOfBytes,
                    self.storedScratchPadCRC,
                    self.storedScratchSeq,
                    self.storedScratchType,
                    self.storedScratchStatus,
                    self.processedScratchPadNumberOfBytes,
                    self.processedScratchPadCRC,
                    self.processedScratchPadSeq,
                    self.processedFirmwareAreaId,
                    self.FWmajorVer,
                    self.FWminorVer,
                    self.FWmaintVer,
                    self.FWdevelVer,
                    self.applicationProcessedScratchPadNumberOfBytes,
                    self.applicationProcessedScratchPadCRC,
                    self.applicationProcessedScratchPadSeq,
                    self.processedApplicationAreaId,
                    self.appMajorVer,
                    self.appMinorVer,
                    self.appMaintVer,
                    self.appDevelVer,
                ) = fields
                self.__is_valid = True
            else:
                print("Unknown message. Message len is", message_len)
        else:
            print("Deserialization failed. Data size:", len(data_bytes))

    def is_valid(self) -> bool:
        return self.__is_valid
