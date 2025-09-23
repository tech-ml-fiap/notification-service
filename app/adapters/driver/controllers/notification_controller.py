from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.domain.entities import NotificationInput
from app.domain.services.notification_service import NotificationService
from app.adapters.driven.auth_gateway_http import HttpAuthGateway
from app.adapters.driven.email_gateway_smtp import SmtpEmailGateway
from app.adapters.driven.email_composer_default import DefaultEmailComposer

router = APIRouter()

_auth = HttpAuthGateway()
_email = SmtpEmailGateway()
_composer = DefaultEmailComposer()
_service = NotificationService(auth=_auth, email=_email, composer=_composer)

class NotifyPayload(BaseModel):
    job_id: str = Field(..., description="ID do job")
    status: str = Field(..., pattern="^(success|error)$", description="success | error")
    user_id: int = Field(..., description="user_id")
    video_url: str | None = Field(None, description="Link do vídeo (em success)")
    error_message: str | None = Field(None, description="Detalhes do erro (em error)")

@router.post("/notify")
def post_notify(p: NotifyPayload):
    try:
        data = NotificationInput(
            job_id=p.job_id,
            status=p.status,
            user_id=p.user_id,
            video_url=p.video_url,
            error_message=p.error_message,
        )
        return _service.execute(data)
    except Exception as e:
        raise HTTPException(400, str(e))
