MODULE = "app.adapters.driven.email_gateway_smtp"

import types
from importlib import import_module
import pytest

m = import_module(MODULE)

# --------- Helpers / Doubles ---------
class FakeSMTP:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged = False
        self.tls_started = False
        self.noop_called = 0
        self.quit_called = 0
        self.sent = []
        # hooks configuráveis por teste
        self.hook_starttls_exc = None
        self.hook_noop_exc = None
        self.hook_sendmail_exc = None

    def ehlo(self):
        return (250, b"ok")

    def starttls(self):
        if self.hook_starttls_exc:
            raise self.hook_starttls_exc
        self.tls_started = True
        return (220, b"ready")

    def login(self, user, pwd):
        self.logged = (user, pwd)
        return (235, b"ok")

    def noop(self):
        self.noop_called += 1
        if self.hook_noop_exc:
            raise self.hook_noop_exc
        return (250, b"ok")

    def quit(self):
        self.quit_called += 1
        return (221, b"bye")

    def sendmail(self, from_addr, to_addrs, data):
        if self.hook_sendmail_exc:
            raise self.hook_sendmail_exc
        self.sent.append((from_addr, tuple(to_addrs), data))
        return {}


class SeqClients:
    """Retorna uma sequência de clientes em chamadas subsequentes."""
    def __init__(self, clients):
        self.clients = list(clients)
        self.i = 0

    def __call__(self):
        c = self.clients[min(self.i, len(self.clients) - 1)]
        self.i += 1
        return c


def _patch_minimal_settings(monkeypatch, **overrides):
    base = dict(
        EMAIL_USE_SSL=False,
        EMAIL_USE_STARTTLS=False,
        EMAIL_HOST="smtp.test",
        EMAIL_PORT=2525,
        SMTP_CONNECT_TIMEOUT=4.0,
        SMTP_OP_TIMEOUT=3.0,
        EMAIL_USER="user@test",
        EMAIL_PASS="s3cr3t",
        EMAIL_FROM="no-reply@test",
        SMTP_MAX_RETRIES=3,
    )
    base.update(overrides)
    monkeypatch.setattr(f"{MODULE}.settings", types.SimpleNamespace(**base), raising=True)


def _patch_smtplib(monkeypatch, smtp_cls=FakeSMTP, smtp_ssl_cls=None):
    monkeypatch.setattr(f"{MODULE}.smtplib.SMTP", smtp_cls, raising=True)
    monkeypatch.setattr(f"{MODULE}.smtplib.SMTP_SSL", smtp_ssl_cls or smtp_cls, raising=True)


def test_connect_with_ssl_and_login(monkeypatch):
    _patch_minimal_settings(
        monkeypatch,
        EMAIL_USE_SSL=True,
        EMAIL_USER="login@test",
        EMAIL_PASS="pwd",
        SMTP_CONNECT_TIMEOUT=10.0,
        SMTP_OP_TIMEOUT=5.0,
    )
    _patch_smtplib(monkeypatch)

    c = m._connect()
    assert isinstance(c, FakeSMTP)
    assert c.host == "smtp.test"
    assert c.port == 2525
    assert c.timeout == 5.0
    assert c.logged == ("login@test", "pwd")


def test_connect_with_starttls_success(monkeypatch):
    _patch_minimal_settings(
        monkeypatch,
        EMAIL_USE_SSL=False,
        EMAIL_USE_STARTTLS=True,
    )
    _patch_smtplib(monkeypatch)

    c = m._connect()
    assert c.tls_started is True
    assert c.logged == ("user@test", "s3cr3t")


def test_connect_with_starttls_fails_but_continues(monkeypatch):
    _patch_minimal_settings(
        monkeypatch,
        EMAIL_USE_SSL=False,
        EMAIL_USE_STARTTLS=True,
    )

    class FakeSMTPErr(FakeSMTP):
        def starttls(self):
            raise RuntimeError("no tls")

    _patch_smtplib(monkeypatch, smtp_cls=FakeSMTPErr)

    c = m._connect()
    assert isinstance(c, FakeSMTPErr)
    assert c.logged == ("user@test", "s3cr3t")


def test_get_client_caches_and_uses_noop(monkeypatch):
    _patch_minimal_settings(monkeypatch)
    _patch_smtplib(monkeypatch)
    monkeypatch.setattr(f"{MODULE}._smtp_client", None, raising=True)

    c1 = m._get_client()
    c2 = m._get_client()
    assert c1 is c2
    assert c1.noop_called == 1


def test_get_client_reconnects_when_noop_fails(monkeypatch):
    _patch_minimal_settings(monkeypatch)
    _patch_smtplib(monkeypatch)
    monkeypatch.setattr(f"{MODULE}._smtp_client", None, raising=True)

    first = FakeSMTP("a", 1, timeout=1)
    first.hook_noop_exc = RuntimeError("broken")
    second = FakeSMTP("b", 2, timeout=2)

    make = SeqClients([first, second])

    def _smtp_factory(host, port, timeout=None):
        c = make()
        c.host, c.port, c.timeout = host, port, timeout
        return c

    monkeypatch.setattr(f"{MODULE}.smtplib.SMTP", _smtp_factory, raising=True)

    c = m._get_client()
    assert c is first
    c2 = m._get_client()
    assert c2 is second
    assert first.quit_called == 1


def test_as_mime_builds_alternative_with_both_parts(monkeypatch):
    _patch_minimal_settings(monkeypatch, EMAIL_FROM="from@test")
    msg = types.SimpleNamespace(
        to="dest@test",
        subject="Assunto",
        text="Texto plano",
        html="<b>HTML</b>",
    )
    mime = m._as_mime(msg)
    assert mime["Subject"] == "Assunto"
    assert mime["From"] == "from@test"
    assert mime["To"] == "dest@test"
    payloads = mime.get_payload()
    assert len(payloads) == 2
    assert payloads[0].get_content_type() == "text/plain"
    assert payloads[1].get_content_type() == "text/html"


def test_send_success(monkeypatch):
    _patch_minimal_settings(monkeypatch, SMTP_MAX_RETRIES=2)
    _patch_smtplib(monkeypatch)
    monkeypatch.setattr(f"{MODULE}._smtp_client", None, raising=True)

    msg = types.SimpleNamespace(
        to="dest@test",
        subject="ok",
        text="t",
        html="<p>t</p>",
    )
    gw = m.SmtpEmailGateway()
    gw.send(msg)
    assert isinstance(m._smtp_client, FakeSMTP)
    assert len(m._smtp_client.sent) == 1
    from_addr, to_addrs, data = m._smtp_client.sent[0]
    assert to_addrs == ("dest@test",)


def test_send_retries_then_success(monkeypatch):
    _patch_minimal_settings(monkeypatch, SMTP_MAX_RETRIES=3)
    monkeypatch.setattr(f"{MODULE}.time.sleep", lambda *_: None, raising=True)

    c1 = FakeSMTP("h", 1)
    c1.hook_sendmail_exc = m.smtplib.SMTPServerDisconnected("boom")
    c2 = FakeSMTP("h", 1)

    seq = SeqClients([c1, c2])

    def factory(host, port, timeout=None):
        c = seq()
        c.host, c.port, c.timeout = host, port, timeout
        return c

    _patch_minimal_settings(monkeypatch)
    monkeypatch.setattr(f"{MODULE}.smtplib.SMTP", factory, raising=True)
    monkeypatch.setattr(f"{MODULE}._smtp_client", None, raising=True)

    msg = types.SimpleNamespace(
        to="dest@test", subject="s", text="t", html="<p>t</p>"
    )
    gw = m.SmtpEmailGateway()
    gw.send(msg)

    assert c1.quit_called == 1
    assert len(c2.sent) == 1


def test_send_non_transient_exception_raises_runtimeerror(monkeypatch):
    _patch_minimal_settings(monkeypatch, SMTP_MAX_RETRIES=3)
    monkeypatch.setattr(f"{MODULE}.time.sleep", lambda *_: None, raising=True)

    c = FakeSMTP("h", 1)
    c.hook_sendmail_exc = ValueError("invalid from")

    monkeypatch.setattr(f"{MODULE}._get_client", lambda: c, raising=True)

    msg = types.SimpleNamespace(
        to="dest@test", subject="x", text="t", html="<p>t</p>"
    )
    gw = m.SmtpEmailGateway()
    with pytest.raises(RuntimeError) as exc:
        gw.send(msg)
    assert "Falha ao enviar e-mail: " in str(exc.value)
    assert c.quit_called == 0


def test_send_exhausts_retries_and_fails(monkeypatch):
    _patch_minimal_settings(monkeypatch, SMTP_MAX_RETRIES=2)
    monkeypatch.setattr(f"{MODULE}.time.sleep", lambda *_: None, raising=True)

    c = FakeSMTP("h", 1)
    c.hook_sendmail_exc = m.smtplib.SMTPServerDisconnected("down")

    monkeypatch.setattr(f"{MODULE}._get_client", lambda: c, raising=True)
    monkeypatch.setattr(f"{MODULE}._smtp_client", c, raising=True)

    msg = types.SimpleNamespace(
        to="dest@test", subject="x", text="t", html="<p>t</p>"
    )
    gw = m.SmtpEmailGateway()
    with pytest.raises(RuntimeError) as exc:
        gw.send(msg)
    s = str(exc.value)
    assert "Falha ao enviar e-mail:" in s
    assert "down" in s
    assert c.quit_called >= 1
