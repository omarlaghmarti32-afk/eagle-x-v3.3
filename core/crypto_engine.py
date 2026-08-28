"""Real cryptographic engine using the cryptography library.

Provides AES-256-GCM encryption, Ed25519 signatures, and key management.
PQC labels remain for hybrid roadmap; classical crypto here is production-grade.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .config import KEY_PATH


class CryptoEngine:
    def __init__(self, key_path: Path = KEY_PATH):
        self.key_path = Path(key_path)
        self._master_key = self._load_or_create_master_key()
        self._private_key, self._public_key = self._load_or_create_signing_keys()

    def _load_or_create_master_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        key = AESGCM.generate_key(bit_length=256)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def _load_or_create_signing_keys(self) -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
        priv_path = self.key_path.with_suffix(".ed25519")
        if priv_path.exists():
            private_key = serialization.load_pem_private_key(
                priv_path.read_bytes(), password=None
            )
            assert isinstance(private_key, Ed25519PrivateKey)
            return private_key, private_key.public_key()

        private_key = Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        priv_path.write_bytes(pem)
        try:
            os.chmod(priv_path, 0o600)
        except OSError:
            pass
        return private_key, private_key.public_key()

    def derive_key(self, context: str) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=context.encode("utf-8"),
        ).derive(self._master_key)

    def encrypt(self, plaintext: str | bytes, aad: Optional[bytes] = None) -> str:
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        aesgcm = AESGCM(self._master_key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext, aad)
        blob = base64.b64encode(nonce + ct).decode("ascii")
        return f"AES256GCM:{blob}"

    def decrypt(self, token: str, aad: Optional[bytes] = None) -> bytes:
        if not token.startswith("AES256GCM:"):
            raise ValueError("Unsupported ciphertext format")
        raw = base64.b64decode(token.split(":", 1)[1])
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(self._master_key)
        return aesgcm.decrypt(nonce, ct, aad)

    def sign(self, data: str | bytes) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        sig = self._private_key.sign(data)
        return base64.b64encode(sig).decode("ascii")

    def verify(self, data: str | bytes, signature_b64: str) -> bool:
        if isinstance(data, str):
            data = data.encode("utf-8")
        try:
            self._public_key.verify(base64.b64decode(signature_b64), data)
            return True
        except Exception:
            return False

    def seal_json(self, obj: Dict[str, Any]) -> Dict[str, str]:
        payload = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        return {
            "ciphertext": self.encrypt(payload),
            "signature": self.sign(payload),
            "sha3": hashlib.sha3_256(payload.encode("utf-8")).hexdigest(),
        }

    def public_key_pem(self) -> str:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def rotate_master_key(self) -> None:
        """Generate a new master key (callers must re-encrypt sensitive data)."""
        key = AESGCM.generate_key(bit_length=256)
        self.key_path.write_bytes(key)
        self._master_key = key
