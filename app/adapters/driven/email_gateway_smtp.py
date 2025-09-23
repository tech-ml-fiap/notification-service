import smtplib, socket, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from infra.settings import settings
from app.domain.entities import EmailMessage
from app.domain.ports import EmailGateway

_smtp_client: Optional[smtplib.SMTP] = None

def _connect() -> smtplib.SMTP:
    if settings.EMAIL_USE_SSL:
        client = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.SMTP_CONNECT_TIMEOUT)
    else:
        client = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=settings.SMTP_CONNECT_TIMEOUT)
        if settings.EMAIL_USE_STARTTLS:
            client.ehlo()
            try:
                client.starttls(); client.ehlo()
            except Exception:
                pass
    if settings.EMAIL_USER and settings.EMAIL_PASS:
        client.login(settings.EMAIL_USER, settings.EMAIL_PASS)
    client.timeout = settings.SMTP_OP_TIMEOUT
    print(settings.EMAIL_USER)
    print(settings.EMAIL_PASS)
    return client

def _get_client() -> smtplib.SMTP:
    global _smtp_client
    try:
        if _smtp_client is None:
            _smtp_client = _connect()
        else:
            _smtp_client.noop()
    except Exception:
        try:
            if _smtp_client: _smtp_client.quit()
        except Exception:
            pass
        _smtp_client = _connect()
    return _smtp_client

def _as_mime(msg: EmailMessage) -> MIMEMultipart:
    m = MIMEMultipart("alternative")
    m["Subject"] = msg.subject
    m["From"] = settings.EMAIL_FROM or settings.EMAIL_USER
    m["To"] = msg.to
    m.attach(MIMEText(msg.text, "plain", "utf-8"))
    m.attach(MIMEText(msg.html, "html", "utf-8"))
    return m

class SmtpEmailGateway(EmailGateway):
    def send(self, message: EmailMessage) -> None:
        mime = _as_mime(message)
        last_exc: Optional[Exception] = None
        for attempt in range(1, settings.SMTP_MAX_RETRIES + 1):
            try:
                client = _get_client()
                client.sendmail(mime["From"], [message.to], mime.as_string())
                return
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPHeloError,
                    smtplib.SMTPDataError, smtplib.SMTPRecipientsRefused, socket.timeout) as e:
                last_exc = e
                time.sleep(min(2 ** attempt, 8))
                try:
                    client.quit()
                except Exception:
                    pass
                finally:
                    globals()["_smtp_client"] = None
            except Exception as e:
                last_exc = e
                break
        raise RuntimeError(f"Falha ao enviar e-mail: {last_exc}")
