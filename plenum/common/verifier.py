from typing import Dict

from abc import abstractmethod

from base58 import b58decode, b58encode
from plenum.common.signing import serializeMsg
from stp_core.crypto.nacl_wrappers import Verifier as NaclVerifier


class Verifier:
    @abstractmethod
    def verify(self, sig, msg) -> bool:
        pass

    def verifyMsg(self, sig, msg: Dict):
        ser = serializeMsg(msg)
        return self.verify(sig, ser)


class DidVerifier(Verifier):
    def __init__(self, verkey, identifier=None):
        self._verkey = None
        self._vr = None
        if identifier:
            rawIdr = b58decode(identifier)
            if len(rawIdr) == 32 and not verkey:  # assume cryptonym
                verkey = identifier

            assert verkey, 'verkey must be provided'
            if verkey[0] == '~':  # abbreviated
                verkey = b58encode(b58decode(identifier) +
                                   b58decode(verkey[1:]))
        self.verkey = verkey

    @property
    def verkey(self):
        return self._verkey

    @verkey.setter
    def verkey(self, value):
        self._verkey = value
        self._vr = NaclVerifier(b58decode(value))

    def verify(self, sig, msg) -> bool:
        return self._vr.verify(sig, msg)
