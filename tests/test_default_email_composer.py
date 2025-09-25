MODULE = "app.adapters.driven.email_composer_default"

from importlib import import_module
from types import SimpleNamespace

DefaultEmailComposer = getattr(import_module(MODULE), "DefaultEmailComposer")


def _identity(email="user@example.com", name="Mateus"):
    return SimpleNamespace(email=email, name=name)


def _data_success(job_id="123", video_url="http://videos/123.mp4"):
    return SimpleNamespace(
        status="success",
        job_id=job_id,
        video_url=video_url,
        error_message=None,
    )


def _data_error(job_id="999", error_message="timeout"):
    return SimpleNamespace(
        status="error",
        job_id=job_id,
        video_url=None,
        error_message=error_message,
    )


def test_compose_success_with_video_url():
    composer = DefaultEmailComposer()
    identity = _identity()
    data = _data_success(job_id="42", video_url="http://cdn/video-42.mp4")

    msg = composer.compose(data, identity)

    assert msg.to == "user@example.com"
    assert msg.subject == "Seu vídeo foi processado (#42)"
    # Texto
    assert "Olá, Mateus!" in msg.text
    assert "Seu vídeo (job 42) foi processado com sucesso." in msg.text
    assert "Link: http://cdn/video-42.mp4" in msg.text
    # HTML
    assert "<strong>Mateus</strong>" in msg.html
    assert "job <strong>42</strong>" in msg.html
    assert '<a href="http://cdn/video-42.mp4">' in msg.html
    assert msg.text == msg.text.strip()
    assert msg.html == msg.html.strip()


def test_compose_success_without_video_url():
    composer = DefaultEmailComposer()
    identity = _identity(name="João")
    data = _data_success(job_id="77", video_url=None)

    msg = composer.compose(data, identity)

    assert msg.to == "user@example.com"
    assert msg.subject == "Seu vídeo foi processado (#77)"
    assert "Link:" not in msg.text
    assert '<a href="' not in msg.html
    assert "Olá, João!" in msg.text
    assert "Seu vídeo (job 77) foi processado com sucesso." in msg.text
    assert "<strong>João</strong>" in msg.html


def test_compose_error_with_detail():
    composer = DefaultEmailComposer()
    identity = _identity(email="dest@ex.com", name="Cliente")
    data = _data_error(job_id="9001", error_message="Falha no encoder")

    msg = composer.compose(data, identity)

    assert msg.to == "dest@ex.com"
    assert msg.subject == "Falha ao processar seu vídeo (#9001)"
    assert "Ocorreu um erro ao processar seu vídeo (job 9001)." in msg.text
    assert "Detalhes: Falha no encoder" in msg.text
    assert "<strong>Falha</strong>" in msg.html
    assert "Detalhes: Falha no encoder" in msg.html


def test_compose_error_without_detail_uses_default_message():
    composer = DefaultEmailComposer()
    identity = _identity(name="Cliente X")
    data = _data_error(job_id="1", error_message=None)

    msg = composer.compose(data, identity)

    assert msg.subject == "Falha ao processar seu vídeo (#1)"
    assert "Detalhes: não informado." in msg.text
    assert "Detalhes: não informado." in msg.html
    assert "Cliente X" in msg.text
    assert "<strong>Cliente X</strong>" in msg.html
