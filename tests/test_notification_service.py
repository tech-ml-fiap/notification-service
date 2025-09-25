import pytest
from unittest.mock import MagicMock

from app.domain.entities import Identity, NotificationInput, EmailMessage
from app.domain.services.notification_service import NotificationService


def _data(**over):
    base = dict(job_id="42", status="success", user_id=7, video_url="http://cdn/v.mp4", error_message=None)
    base.update(over)
    return NotificationInput(**base)


def _msg():
    return EmailMessage(
        to="user@example.com",
        subject="s",
        text="t",
        html="<p>t</p>",
    )


def test_execute_happy_path_calls_all_dependencies_and_returns_ok():
    auth = MagicMock()
    email = MagicMock()
    composer = MagicMock()

    auth.resolve_identity.return_value = Identity(email="user@example.com", name="Mateus")
    composer.compose.return_value = _msg()

    svc = NotificationService(auth=auth, email=email, composer=composer)
    data = _data()

    result = svc.execute(data)

    assert result == {"ok": True}
    auth.resolve_identity.assert_called_once_with(7)
    composer.compose.assert_called_once()
    called_data, called_identity = composer.compose.call_args.args
    assert called_data is data
    assert called_identity == Identity(email="user@example.com", name="Mateus")
    email.send.assert_called_once()
    sent_msg = email.send.call_args.args[0]
    assert isinstance(sent_msg, EmailMessage)
    assert sent_msg.to == "user@example.com"


def test_execute_when_composer_raises_propagates_and_does_not_send_email():
    auth = MagicMock()
    email = MagicMock()
    composer = MagicMock()

    auth.resolve_identity.return_value = Identity(email="u@x.com", name="X")
    composer.compose.side_effect = RuntimeError("boom")

    svc = NotificationService(auth=auth, email=email, composer=composer)
    data = _data()

    with pytest.raises(RuntimeError, match="boom"):
        svc.execute(data)

    email.send.assert_not_called()


def test_execute_when_email_gateway_raises_propagates():
    auth = MagicMock()
    email = MagicMock()
    composer = MagicMock()

    auth.resolve_identity.return_value = Identity(email="u@x.com", name="X")
    composer.compose.return_value = _msg()
    email.send.side_effect = ValueError("smtp down")

    svc = NotificationService(auth=auth, email=email, composer=composer)
    data = _data(status="error", error_message="e")

    with pytest.raises(ValueError, match="smtp down"):
        svc.execute(data)

    auth.resolve_identity.assert_called_once_with(7)
    composer.compose.assert_called_once()
