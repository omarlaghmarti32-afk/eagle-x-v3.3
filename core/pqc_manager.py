"""Hybrid crypto facade: AES/Ed25519 always + real PQC when liboqs is present."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, Optional

from .crypto_engine import CryptoEngine
from .pqc_real import RealPQC

logger = logging.getLogger("EAGLE-X")


class PQCManager:
    def __init__(self):
        self.crypto = CryptoEngine()
        self.pqc = RealPQC()
        if self.pqc.available:
            self.algorithm = f"{self.pqc.kem_alg} + AES-256-GCM"
            self.signature_scheme = f"{self.pqc.sig_alg} + Ed25519"
            self.mode = "hybrid-pqc"
        else:
            self.algorithm = "AES-256-GCM (PQC optional — install liboqs-python)"
            self.signature_scheme = "Ed25519 (PQC optional)"
            self.mode = "classical"
        logger.info(f"Crypto manager online mode={self.mode}")

    def encrypt(self, data: str) -> str:
        return self.crypto.encrypt(data)

    def decrypt(self, token: str) -> str:
        return self.crypto.decrypt(token).decode("utf-8")

    def sign(self, data: str) -> str:
        return self.crypto.sign(data)

    def verify_signature(self, data: str, signature: str) -> bool:
        return self.crypto.verify(data, signature)

    def seal(self, obj: Dict[str, Any]) -> Dict[str, str]:
        sealed = self.crypto.seal_json(obj)
        if self.pqc.available:
            import json

            payload = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()
            signed = self.pqc.sign(payload)
            if signed:
                sig, pub, _sk = signed
                sealed["pqc_signature"] = self.pqc.b64(sig)
                sealed["pqc_public_key"] = self.pqc.b64(pub)
                sealed["pqc_alg"] = self.pqc.sig_alg
        return sealed

    def kem_demo(self) -> Optional[Dict[str, str]]:
        """Run a real ML-KEM encapsulate cycle when available."""
        result = self.pqc.encapsulate()
        if not result:
            return None
        return {
            "algorithm": result.algorithm,
            "public_key": self.pqc.b64(result.public_key),
            "ciphertext": self.pqc.b64(result.ciphertext),
            "shared_secret_sha3": hashlib.sha3_256(result.shared_secret).hexdigest(),
        }

    def pqc_label_hash(self, data: str) -> str:
        salt = os.urandom(8).hex()
        digest = hashlib.sha3_512((data + salt).encode()).hexdigest()
        return f"PQC-LABEL:{self.pqc.kem_alg if self.pqc.available else 'N/A'}:{salt}:{digest}"

    def get_status(self) -> dict:
        return {
            "mode": self.mode,
            "algorithm": self.algorithm,
            "signature_scheme": self.signature_scheme,
            "active_confidentiality": "AES-256-GCM",
            "active_integrity": "Ed25519",
            "pqc": self.pqc.status(),
            "status": "Active",
            "public_key_pem": self.crypto.public_key_pem(),
        }
