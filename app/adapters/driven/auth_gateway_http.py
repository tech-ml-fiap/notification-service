# app/adapters/driven/auth_gateway_http.py
import json
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass
from infra.settings import settings
from app.domain.entities import Identity
from app.domain.ports import AuthGateway

@dataclass
class HttpAuthGateway(AuthGateway):
    def resolve_identity(self, user_id: str) -> Identity:
        url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/api/client/{user_id}"
        req = urllib.request.Request(
            url=url,
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=settings.AUTH_TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 404:
                raise ValueError("Cliente não encontrado")
            raise

        email = (data or {}).get("email")
        name = (data or {}).get("name") or "cliente"
        if not email:
            raise ValueError("Auth não retornou e-mail")
        return Identity(email=email, name=name)
