import pytest

from api.connectors.whatsapp.webhook.verify import (
    WebhookChallengeError,
    verify_webhook_challenge,
)


def test_verify_webhook_challenge_ok() -> None:
    challenge = verify_webhook_challenge(
        hub_mode="subscribe",
        hub_verify_token="token",
        hub_challenge="abc123",
        expected_token="token",
    )
    assert challenge == "abc123"


def test_verify_webhook_challenge_missing_token() -> None:
    with pytest.raises(WebhookChallengeError, match="missing_verify_token"):
        verify_webhook_challenge(
            hub_mode="subscribe",
            hub_verify_token="token",
            hub_challenge="x",
            expected_token=None,
        )


def test_verify_webhook_challenge_invalid_token() -> None:
    with pytest.raises(WebhookChallengeError, match="verification_failed"):
        verify_webhook_challenge(
            hub_mode="subscribe",
            hub_verify_token="wrong",
            hub_challenge="x",
            expected_token="token",
        )
