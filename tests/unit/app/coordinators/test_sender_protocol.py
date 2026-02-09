import pytest

from app.coordinators.whatsapp.flows.sender import FlowSender
from app.protocols.crypto import FlowCryptoError


class FakeCrypto:
    def __init__(self) -> None:
        self.private_loaded = False

    def load_private_key(self, private_key_pem: str, passphrase: str | None = None):
        self.private_loaded = True
        return "PRIVATE"

    def decrypt_aes_key(self, private_key, encrypted_aes_key: str) -> bytes:
        return b"AESKEY"

    def decrypt_flow_data(
        self,
        aes_key: bytes,
        encrypted_flow_data: str,
        initial_vector: str,
    ) -> dict:
        return {"flow_token": "t", "action": "ok", "screen": "s", "data": {}, "version": "1"}

    def encrypt_flow_response(self, response_data: dict, aes_key: bytes | None = None) -> dict:
        return {"payload": "encrypted"}

    def validate_flow_signature(self, payload: bytes, signature: str, secret: bytes) -> bool:
        return signature == "valid"


def test_flow_sender_calls_crypto_methods():
    crypto = FakeCrypto()
    sender = FlowSender(crypto=crypto, private_key_pem="pem", flow_endpoint_secret="secret")

    assert crypto.private_loaded is True

    assert sender.validate_signature(b"payload", "valid") is True

    df = sender.decrypt_request("enc_key", "enc_data", "iv")
    assert df.flow_token == "t"

    out = sender.encrypt_response({})
    assert out["payload"] == "encrypted"


def test_flow_sender_wraps_private_key_errors():
    class BadCrypto(FakeCrypto):
        def load_private_key(self, private_key_pem: str, passphrase: str | None = None):
            raise RuntimeError("bad key")

    with pytest.raises(FlowCryptoError):
        FlowSender(crypto=BadCrypto(), private_key_pem="pem", flow_endpoint_secret="secret")
