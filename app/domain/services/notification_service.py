from app.domain.entities import NotificationInput, EmailMessage
from app.domain.ports import AuthGateway, EmailGateway, EmailComposer

class NotificationService:
    def __init__(self, auth: AuthGateway, email: EmailGateway, composer: EmailComposer):
        self._auth = auth
        self._email = email
        self._composer = composer

    def execute(self, data: NotificationInput) -> dict:
        identity = self._auth.resolve_identity(data.user_id)
        print(identity)
        message: EmailMessage = self._composer.compose(data, identity)
        self._email.send(message)
        return {"ok": True}
