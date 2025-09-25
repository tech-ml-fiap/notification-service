import pytest
from app.domain.ports import AuthGateway, EmailGateway, EmailComposer
from app.domain.entities import Identity, NotificationInput, EmailMessage


def test_abstract_classes_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AuthGateway()
    with pytest.raises(TypeError):
        EmailGateway()
    with pytest.raises(TypeError):
        EmailComposer()


class DummyAuth(AuthGateway):
    def resolve_identity(self, user_id: id) -> Identity:
        return Identity(email=f"user{user_id}@example.com", name="User")


class DummyEmail(EmailGateway):
    def __init__(self):
        self.sent = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class DummyComposer(EmailComposer):
    def compose(self, data: NotificationInput, identity: Identity) -> EmailMessage:
        return EmailMessage(
            to=identity.email,
            subject=f"{data.status}:{data.job_id}",
            text=f"hello {identity.name}",
            html=f"<p>hello {identity.name}</p>",
        )


def test_concrete_authgateway_resolve_identity():
    gw = DummyAuth()
    ident = gw.resolve_identity(42)
    assert isinstance(ident, Identity)
    assert ident.email == "user42@example.com"
    assert ident.name == "User"


def test_concrete_emailgateway_send_and_store_message():
    gw = DummyEmail()
    msg = EmailMessage(
        to="a@b.com", subject="s", text="t", html="<p>t</p>"
    )
    assert gw.send(msg) is None
    assert gw.sent == [msg]


def test_concrete_emailcomposer_compose_message():
    comp = DummyComposer()
    data = NotificationInput(job_id="123", status="success", user_id=7)
    ident = Identity(email="u@example.com", name="Mateus")
    out = comp.compose(data, ident)

    assert isinstance(out, EmailMessage)
    assert out.to == "u@example.com"
    assert out.subject == "success:123"
    assert "Mateus" in out.text
    assert "<p>hello Mateus</p>" in out.html
