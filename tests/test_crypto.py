import os
from pathlib import Path

from core.crypto_engine import CryptoEngine


def test_encrypt_decrypt_roundtrip(tmp_path):
    key_path = tmp_path / "master.key"
    engine = CryptoEngine(key_path=key_path)
    token = engine.encrypt("hello eagle")
    assert token.startswith("AES256GCM:")
    assert engine.decrypt(token) == b"hello eagle"


def test_sign_verify(tmp_path):
    engine = CryptoEngine(key_path=tmp_path / "master.key")
    sig = engine.sign("payload")
    assert engine.verify("payload", sig) is True
    assert engine.verify("tampered", sig) is False


def test_seal_json(tmp_path):
    engine = CryptoEngine(key_path=tmp_path / "master.key")
    sealed = engine.seal_json({"a": 1, "b": "x"})
    assert "ciphertext" in sealed and "signature" in sealed and "sha3" in sealed
