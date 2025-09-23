from dataclasses import dataclass
from typing import Optional, Literal

Status = Literal["success", "error"]

@dataclass(frozen=True)
class Identity:
    email: str
    name: str

@dataclass(frozen=True)
class NotificationInput:
    job_id: str
    status: Status
    user_id: int
    video_url: Optional[str] = None
    error_message: Optional[str] = None

@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str
