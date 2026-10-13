
import smtplib

from app.core.config import settings
from app.tasks.notifications import notify_request_created


def test_notification_skips_without_smtp(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", None)

    result = notify_request_created.run(
        request_id=12,
        citizen_id=3,
        title="Repair broken road",
        recipient_email="citizen@example.com",
    )

    assert result == {"status": "skipped", "request_id": 12}


def test_notification_propagates_smtp_failure(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)

    class FailingSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, message):
            raise smtplib.SMTPException("Simulated delivery failure")

    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)

    try:
        notify_request_created.run(
            request_id=12,
            citizen_id=3,
            title="Repair broken road",
            recipient_email="citizen@example.com",
        )
    except smtplib.SMTPException as exc:
        assert str(exc) == "Simulated delivery failure"
    else:
        raise AssertionError("SMTP failure should propagate from the task")


def test_notification_sends_email(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert host == "smtp.example.com"
            assert port == 587
            assert timeout == 15

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["tls"] = True

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    result = notify_request_created.run(
        request_id=12,
        citizen_id=3,
        title="Repair broken road",
        recipient_email="citizen@example.com",
    )

    assert result == {"status": "sent", "request_id": 12}
    assert sent["message"]["To"] == "citizen@example.com"
    assert sent["message"]["From"] == "noreply@example.com"
    assert "12" in sent["message"]["Subject"]
    assert "Repair broken road" in sent["message"].get_content()
    assert sent["tls"] is True
