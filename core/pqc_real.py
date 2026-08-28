"""Optional real post-quantum cryptography via liboqs-python / oqs.

Uses NIST standards when available:
  - ML-KEM (FIPS 203) for key encapsulation
  - ML-DSA (FIPS 204) for signatures

Falls back gracefully if native liboqs is not installed.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("EAGLE-X")

_OQS = None
_AVAILABLE = False
_KEM_ALG = "ML-KEM-768"
_SIG_ALG = "ML-DSA-65"

try:
    import oqs  # type: ignore

    _OQS = oqs
    enabled_kems = set(oqs.get_enabled_kem_mechanisms())
    enabled_sigs = set(oqs.get_enabled_sig_mechanisms())
    if "ML-KEM-768" in enabled_kems:
        _KEM_ALG = "ML-KEM-768"
    elif "Kyber768" in enabled_kems:
        _KEM_ALG = "Kyber768"
    if "ML-DSA-65" in enabled_sigs:
        _SIG_ALG = "ML-DSA-65"
    elif "Dilithium3" in enabled_sigs:
        _SIG_ALG = "Dilithium3"
    _AVAILABLE = True
    logger.info(f"liboqs available: KEM={_KEM_ALG} SIG={_SIG_ALG}")
except Exception as e:
    logger.info(f"liboqs not available ({e}); classical crypto only")


@dataclass
class KEMResult:
    public_key: bytes
    secret_key: bytes
    ciphertext: bytes
    shared_secret: bytes
    algorithm: str


class RealPQC:
    """Thin wrapper around liboqs mechanisms."""

    def __init__(self):
        self.available = _AVAILABLE
        self.kem_alg = _KEM_ALG
        self.sig_alg = _SIG_ALG

    def encapsulate(self) -> Optional[KEMResult]:
        if not self.available or _OQS is None:
            return None
        with _OQS.KeyEncapsulation(self.kem_alg) as kem:
            public_key = kem.generate_keypair()
            secret_key = kem.export_secret_key()
            ciphertext, shared_secret = kem.encap_secret(public_key)
            return KEMResult(
                public_key=public_key,
                secret_key=secret_key,
                ciphertext=ciphertext,
                shared_secret=shared_secret,
                algorithm=self.kem_alg,
            )

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> Optional[bytes]:
        if not self.available or _OQS is None:
            return None
        with _OQS.KeyEncapsulation(self.kem_alg, secret_key) as kem:
            return kem.decap_secret(ciphertext)

    def sign(self, message: bytes) -> Optional[Tuple[bytes, bytes, bytes]]:
        """Returns (signature, public_key, secret_key) or None."""
        if not self.available or _OQS is None:
            return None
        with _OQS.Signature(self.sig_alg) as sig:
            public_key = sig.generate_keypair()
            secret_key = sig.export_secret_key()
            signature = sig.sign(message)
            return signature, public_key, secret_key

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        if not self.available or _OQS is None:
            return False
        with _OQS.Signature(self.sig_alg) as sig:
            return bool(sig.verify(message, signature, public_key))

    def status(self) -> dict:
        return {
            "available": self.available,
            "kem": self.kem_alg if self.available else None,
            "signature": self.sig_alg if self.available else None,
            "backend": "liboqs" if self.available else "none",
        }

    @staticmethod
    def b64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")
