import io
import json
import types
import pytest
from urllib.error import HTTPError
from app.adapters.driven.auth_gateway_http import HttpAuthGateway
from app.domain.entities import Identity


class _MockHTTPResponse:
    def __init__(self, payload: dict, status=200):
        self._bytes = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_http_error(code: int) -> HTTPError:
    return HTTPError(
        url="http://example/auth",
        code=code,
        msg=str(code),
        hdrs=None,
        fp=io.BytesIO(b""),
    )


def test_resolve_identity_success(monkeypatch):
    monkeypatch.setattr(
        "app.adapters.driven.auth_gateway_http.settings",
        types.SimpleNamespace(AUTH_SERVICE_URL="http://clientservice-web:8000/", AUTH_TIMEOUT=3),
        raising=True,
    )

    def _urlopen(req, timeout):
        expected = "http://clientservice-web:8000/api/client/42"
        assert req.full_url == expected
        assert timeout == 3
        return _MockHTTPResponse({"email": "u@example.com", "name": "Mateus"})

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    gw = HttpAuthGateway()
    ident = gw.resolve_identity("42")
    assert isinstance(ident, Identity)
    assert ident.email == "u@example.com"
    assert ident.name == "Mateus"


def test_resolve_identity_defaults_name_when_missing(monkeypatch):
    monkeypatch.setattr(
        "app.adapters.driven.auth_gateway_http.settings",
        types.SimpleNamespace(AUTH_SERVICE_URL="http://auth", AUTH_TIMEOUT=1),
        raising=True,
    )

    def _urlopen(req, timeout):
        assert req.full_url == "http://auth/api/client/abc"
        assert timeout == 1
        return _MockHTTPResponse({"email": "no-name@example.com"})

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    gw = HttpAuthGateway()
    ident = gw.resolve_identity("abc")
    assert ident.email == "no-name@example.com"
    assert ident.name == "cliente"


def test_resolve_identity_404_raises_value_error(monkeypatch):
    monkeypatch.setattr(
        "app.adapters.driven.auth_gateway_http.settings",
        types.SimpleNamespace(AUTH_SERVICE_URL="http://auth", AUTH_TIMEOUT=2),
        raising=True,
    )

    def _urlopen(*args, **kwargs):
        raise _make_http_error(404)

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    gw = HttpAuthGateway()
    with pytest.raises(ValueError) as exc:
        gw.resolve_identity("not-found")
    assert "Cliente não encontrado" in str(exc.value)


def test_resolve_identity_missing_email_and_http_500(monkeypatch):
    monkeypatch.setattr(
        "app.adapters.driven.auth_gateway_http.settings",
        types.SimpleNamespace(AUTH_SERVICE_URL="http://auth", AUTH_TIMEOUT=2),
        raising=True,
    )

    def _ok_without_email(*args, **kwargs):
        return _MockHTTPResponse({"name": "Qualquer"})

    monkeypatch.setattr("urllib.request.urlopen", _ok_without_email)
    gw = HttpAuthGateway()
    with pytest.raises(ValueError) as exc:
        gw.resolve_identity("sem-email")
    assert "Auth não retornou e-mail" in str(exc.value)

    def _raise_500(*args, **kwargs):
        raise _make_http_error(500)

    monkeypatch.setattr("urllib.request.urlopen", _raise_500)
    with pytest.raises(HTTPError) as exc2:
        gw.resolve_identity("boom")
    assert exc2.value.code == 500
