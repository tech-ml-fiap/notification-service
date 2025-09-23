from abc import ABC, abstractmethod
from app.domain.entities import Identity, NotificationInput, EmailMessage

class AuthGateway(ABC):
    @abstractmethod
    def resolve_identity(self, user_id: id) -> Identity:
        ...

class EmailGateway(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        ...

class EmailComposer(ABC):
    @abstractmethod
    def compose(self, data: NotificationInput, identity: Identity) -> EmailMessage:
        ...
