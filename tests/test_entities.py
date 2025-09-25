import pytest
from dataclasses import FrozenInstanceError
from app.domain.entities import Identity, NotificationInput, EmailMessage

def test_identity_dataclass_frozen_and_fields():
    i = Identity(email="u@example.com", name="Mateus")
    assert i.email == "u@example.com"
    assert i.name == "Mateus"
    with pytest.raises(FrozenInstanceError):
        i.email = "x@example.com"
    # equality / hashing
    i2 = Identity(email="u@example.com", name="Mateus")
    i3 = Identity(email="v@example.com", name="Mateus")
    assert i == i2
    assert i != i3
    assert hash(i) == hash(i2)
    assert "Identity" in repr(i)

def test_notification_input_success_defaults_and_frozen():
    n = NotificationInput(job_id="42", status="success", user_id=7)
    assert n.job_id == "42"
    assert n.status == "success"
    assert n.user_id == 7
    assert n.video_url is None
    assert n.error_message is None
    with pytest.raises(FrozenInstanceError):
        n.status = "error"  # type: ignore[attr-defined]
    # equality / hashing
    n2 = NotificationInput(job_id="42", status="success", user_id=7)
    n3 = NotificationInput(job_id="43", status="success", user_id=7)
    assert n == n2
    assert n != n3
    assert hash(n) == hash(n2)
    assert "NotificationInput" in repr(n)

def test_notification_input_error_with_fields_set():
    n = NotificationInput(
        job_id="99",
        status="error",
        user_id=1,
        video_url="http://cdn/vid.mp4",
        error_message="timeout",
    )
    assert n.status == "error"
    assert n.video_url == "http://cdn/vid.mp4"
    assert n.error_message == "timeout"

def test_email_message_dataclass_frozen_and_repr():
    m = EmailMessage(
        to="dest@example.com",
        subject="Assunto",
        text="texto",
        html="<p>html</p>",
    )
    assert m.to == "dest@example.com"
    assert m.subject == "Assunto"
    assert m.text == "texto"
    assert m.html == "<p>html</p>"
    with pytest.raises(FrozenInstanceError):
        m.to = "x@y.com"
    # equality / hashing
    m2 = EmailMessage(
        to="dest@example.com",
        subject="Assunto",
        text="texto",
        html="<p>html</p>",
    )
    m3 = EmailMessage(
        to="other@example.com",
        subject="Assunto",
        text="texto",
        html="<p>html</p>",
    )
    assert m == m2
    assert m != m3
    assert hash(m) == hash(m2)
    assert "EmailMessage" in repr(m)
