"""Hybrid crypto facade: real AES/Ed25519 + labeled PQC roadmap layer."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict

from .crypto_engine import CryptoEngine

logger = logging.getLogger("EAGLE-X")


class PQCManager:
    """Facade kept for API compatibility.

    Real confidentiality/integrity: AES-256-GCM + Ed25519.
    PQC algorithm names document the intended migration path (Kyber/Dilithium).
    """

    def __init__(self):
        self.algorithm = "Kyber-768 (roadmap) + AES-256-GCM (active)"
        self.signature_scheme = "Dilithium-2 (roadmap) + Ed25519 (active)"
        self.crypto = CryptoEngine()
        logger.info("Crypto manager online (AES-256-GCM + Ed25519 active)")

    def encrypt(self, data: str) -> str:
        return self.crypto.encrypt(data)

    def decrypt(self, token: str) -> str:
        return self.crypto.decrypt(token).decode("utf-8")

    def sign(self, data: str) -> str:
        return self.crypto.sign(data)

    def verify_signature(self, data: str, signature: str) -> bool:
        return self.crypto.verify(data, signature)

    def seal(self, obj: Dict[str, Any]) -> Dict[str, str]:
        return self.crypto.seal_json(obj)

    def pqc_label_hash(self, data: str) -> str:
        """Non-secret label hash for compatibility with older clients."""
        salt = os.urandom(8).hex()
        digest = hashlib.sha3_512((data + salt).encode()).hexdigest()
        return f"PQC-LABEL:Kyber-768:{salt}:{digest}"

    def get_status(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "signature_scheme": self.signature_scheme,
            "active_confidentiality": "AES-256-GCM",
            "active_integrity": "Ed25519",
            "pqc_status": "roadmap-labeled",
            "status": "Active",
            "public_key_pem": self.crypto.public_key_pem(),
        }
