from unittest.mock import Mock
from src.alerts.engine import AlertEngine


# -----------------------------
# 1. Provider failure handling
# -----------------------------
def test_provider_failure_does_not_crash_engine():
    provider = Mock()
    provider.send.side_effect = Exception("Provider down")

    engine = AlertEngine(providers=[provider])

    result = engine.send_alert(
        location="Accra",
        score=80,
        risk_tier="HIGH",
    )

    assert result is not None
    assert result.get("failed") >= 1


# -----------------------------
# 2. Rate limit blocking
# -----------------------------
def test_rate_limit_blocks_sending():
    limiter = Mock()
    limiter.can_send.return_value = False

    provider = Mock()

    engine = AlertEngine(
        providers=[provider],
        rate_limiter=limiter,
    )

    result = engine.send_alert(
        location="Tema",
        score=90,
        risk_tier="CRITICAL",
    )

    assert result["blocked"] is True
    provider.send.assert_not_called()


# -----------------------------
# 3. Partial failure scenario
# -----------------------------
def test_partial_provider_failure():
    good_provider = Mock()
    bad_provider = Mock()
    bad_provider.send.side_effect = Exception("SMS failed")

    engine = AlertEngine(providers=[good_provider, bad_provider])

    result = engine.send_alert(
        location="Accra",
        score=78,
        risk_tier="HIGH",
    )

    assert result["sent"] >= 1
    assert result["failed"] >= 1


# -----------------------------
# 4. Force override bypasses limiter
# -----------------------------
def test_force_override_bypasses_rate_limit():
    limiter = Mock()
    limiter.can_send.return_value = False

    provider = Mock()

    engine = AlertEngine(
        providers=[provider],
        rate_limiter=limiter,
    )

    result = engine.send_alert(
        location="Accra",
        score=95,
        risk_tier="CRITICAL",
        force=True,
    )

    assert result["blocked"] is False
    provider.send.assert_called_once()


# -----------------------------
# 5. Empty provider list
# -----------------------------
def test_empty_provider_list():
    engine = AlertEngine(providers=[])

    result = engine.send_alert(
        location="Accra",
        score=70,
        risk_tier="HIGH",
    )

    assert result["sent"] == 0
    assert result["failed"] == 0


# -----------------------------
# 6. Formatter integration called
# -----------------------------
def test_formatter_is_called(mocker):
    formatter_mock = Mock()
    formatter_mock.format_alert.return_value = "ALERT MESSAGE"

    engine = AlertEngine(
        providers=[Mock()],
        formatter=formatter_mock,
    )

    engine.send_alert(
        location="Accra",
        score=88,
        risk_tier="HIGH",
    )

    formatter_mock.format_alert.assert_called()


# -----------------------------
# 7. Provider receives formatted message
# -----------------------------
def test_provider_receives_formatted_message():
    provider = Mock()

    engine = AlertEngine(providers=[provider])

    engine.send_alert(
        location="Accra",
        score=88,
        risk_tier="HIGH",
    )

    provider.send.assert_called()
    args, kwargs = provider.send.call_args

    # Ensure message is passed
    assert hasattr(args[0], "message")
    assert "ALERT" in payload.message or "flood" in payload.message.lower()
