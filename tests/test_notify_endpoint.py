MODULE = "app.adapters.driver.controllers.notification_controller"

from importlib import import_module
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app_and_patch_service(monkeypatch, *, side_effect=None, return_value=None):
    mod = import_module(MODULE)

    class FakeService:
        def __init__(self, side_effect=None, return_value=None):
            self.calls = []
            self.side_effect = side_effect
            self.return_value = return_value

        def execute(self, data):
            self.calls.append(data)
            if self.side_effect:
                raise self.side_effect
            return self.return_value if self.return_value is not None else {"ok": True}

    fake = FakeService(side_effect=side_effect, return_value=return_value)
    monkeypatch.setattr(mod, "_service", fake, raising=True)

    app = FastAPI()
    app.include_router(mod.router)
    return mod, fake, TestClient(app)


def test_post_notify_success_flow(monkeypatch):
    _, fake, client = _make_app_and_patch_service(
        monkeypatch,
        return_value={"ok": True, "echo": "success"},
    )

    payload = {
        "job_id": "42",
        "status": "success",
        "user_id": 7,
        "video_url": "http://cdn/video-42.mp4",
        "error_message": None,
    }
    r = client.post("/notify", json=payload)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "echo": "success"}

    assert len(fake.calls) == 1
    called = fake.calls[0]
    assert called.job_id == "42"
    assert called.status == "success"
    assert called.user_id == 7
    assert called.video_url == "http://cdn/video-42.mp4"
    assert called.error_message is None


def test_post_notify_error_flow(monkeypatch):
    _, fake, client = _make_app_and_patch_service(
        monkeypatch,
        return_value={"ok": True, "echo": "error"},
    )

    payload = {
        "job_id": "9001",
        "status": "error",
        "user_id": 99,
        "video_url": None,
        "error_message": "timeout",
    }
    r = client.post("/notify", json=payload)
    assert r.status_code == 200
    assert r.json() == {"ok": True, "echo": "error"}

    assert len(fake.calls) == 1
    called = fake.calls[0]
    assert called.job_id == "9001"
    assert called.status == "error"
    assert called.user_id == 99
    assert called.video_url is None
    assert called.error_message == "timeout"


def test_post_notify_invalid_status_returns_422(monkeypatch):
    _, _, client = _make_app_and_patch_service(monkeypatch)

    payload = {
        "job_id": "x",
        "status": "pending",
        "user_id": 1,
        "video_url": None,
        "error_message": None,
    }
    r = client.post("/notify", json=payload)
    assert r.status_code == 422


def test_post_notify_service_raises_returns_400(monkeypatch):
    err = RuntimeError("boom")
    _, fake, client = _make_app_and_patch_service(monkeypatch, side_effect=err)

    payload = {
        "job_id": "77",
        "status": "success",
        "user_id": 5,
        "video_url": None,
        "error_message": None,
    }
    r = client.post("/notify", json=payload)
    assert r.status_code == 400
    assert r.json()["detail"] == "boom"

    assert len(fake.calls) == 1
    assert fake.calls[0].job_id == "77"
