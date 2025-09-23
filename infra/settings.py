import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    # Auth
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://clientservice-web:8000")
    AUTH_TIMEOUT: float = float(os.getenv("AUTH_TIMEOUT", "4"))

    # SMTP
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER: str | None = os.getenv("EMAIL_USER")
    EMAIL_PASS: str | None = os.getenv("EMAIL_PASS")
    EMAIL_FROM: str | None = os.getenv("EMAIL_FROM", os.getenv("EMAIL_USER"))
    EMAIL_USE_SSL: bool = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
    EMAIL_USE_STARTTLS: bool = os.getenv("EMAIL_USE_STARTTLS", "true").lower() == "true"

    SMTP_CONNECT_TIMEOUT: float = float(os.getenv("SMTP_CONNECT_TIMEOUT", "7"))
    SMTP_OP_TIMEOUT: float = float(os.getenv("SMTP_OP_TIMEOUT", "10"))
    SMTP_MAX_RETRIES: int = int(os.getenv("SMTP_MAX_RETRIES", "3"))

settings = Settings()
