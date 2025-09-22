import json
import os
import smtplib
import socket
import time
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# ------- Config por ambiente -------
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

CUSTOMER_API = os.getenv("CUSTOMER_SERVICE_URL")

SMTP_CONNECT_TIMEOUT = float(os.getenv("SMTP_CONNECT_TIMEOUT", "7"))
SMTP_OP_TIMEOUT = float(os.getenv("SMTP_OP_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("SMTP_MAX_RETRIES", "3"))

# Conexão SMTP cacheada entre invocações (Lambda reusa container)
_smtp_client: Optional[smtplib.SMTP] = None


def _smtp_connect() -> smtplib.SMTP:
    """Abre conexão SMTP com STARTTLS e autentica."""
    client = smtplib.SMTP(host=EMAIL_HOST, port=EMAIL_PORT, timeout=SMTP_CONNECT_TIMEOUT)
    client.ehlo()
    client.starttls()
    client.ehlo()
    if EMAIL_USER and EMAIL_PASS:
        client.login(EMAIL_USER, EMAIL_PASS)
    # Ajusta timeout para operações de sendmail
    client.timeout = SMTP_OP_TIMEOUT
    return client


def _smtp_get_client() -> smtplib.SMTP:
    """Retorna cliente SMTP reutilizável; reconecta se necessário."""
    global _smtp_client
    try:
        if _smtp_client is None:
            _smtp_client = _smtp_connect()
        else:
            # NOOP/ehlo pra testar conexão; se quebrar, reconecta
            _smtp_client.noop()
    except Exception:
        try:
            if _smtp_client:
                _smtp_client.quit()
        except Exception:
            pass
        _smtp_client = _smtp_connect()
    return _smtp_client


def _resolve_email(payload: dict) -> Optional[str]:
    if payload.get("customer_email"):
        return payload["customer_email"]
    cpf = payload.get("customer_cpf")
    if not cpf or not CUSTOMER_API:
        return None
    url = f"{CUSTOMER_API}{cpf}"
    with urllib.request.urlopen(url, timeout=3) as r:
        data = json.loads(r.read().decode())
        return data.get("email")


def _build_email(payload: dict) -> tuple[str, str, str]:
    name = payload.get("customer_name", "cliente")
    job_id = payload["job_id"]
    status = payload["status"]

    if status == "success":
        subject = f"Seu vídeo foi processado (#{job_id})"
        text = (
            f"Olá, {name}!\n\n"
            f"Seu vídeo (job {job_id}) foi processado com sucesso.\n"
            f"{'Link: ' + payload['video_url'] if payload.get('video_url') else ''}\n\n"
            "Obrigado por usar nosso serviço."
        )
        html_link = f'<p><a href="{payload["video_url"]}">Abrir vídeo</a></p>' if payload.get("video_url") else ""
        html = f"""
        <p>Olá, <strong>{name}</strong>!</p>
        <p>Seu vídeo (job <strong>{job_id}</strong>) foi processado com sucesso.</p>
        {html_link}
        <p>Obrigado por usar nosso serviço.</p>
        """
    else:
        subject = f"Falha ao processar seu vídeo (#{job_id})"
        detail = payload.get("error_message", "não informado.")
        text = (
            f"Olá, {name}!\n\n"
            f"Ocorreu um erro ao processar seu vídeo (job {job_id}).\n"
            f"Detalhes: {detail}\n\n"
            "Tente novamente mais tarde."
        )
        html = f"""
        <p>Olá, <strong>{name}</strong>!</p>
        <p><strong>Falha</strong> ao processar seu vídeo (job <strong>{job_id}</strong>).</p>
        <p>Detalhes: {detail}</p>
        <p>Tente novamente mais tarde.</p>
        """

    return subject, text.strip(), html.strip()


def _compose_message(to_email: str, subject: str, text: str, html: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM or EMAIL_USER
    msg["To"] = to_email

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _send_email_smtp(to_email: str, subject: str, text: str, html: str):
    msg = _compose_message(to_email, subject, text, html)

    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = _smtp_get_client()
            client.sendmail(msg["From"], [to_email], msg.as_string())
            return
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPHeloError,
                smtplib.SMTPDataError, smtplib.SMTPRecipientsRefused, socket.timeout) as e:
            last_exc = e
            # pequeno backoff exponencial
            time.sleep(min(2 ** attempt, 8))
            # força reconexão no próximo loop
            try:
                client.quit()
            except Exception:
                pass
            finally:
                globals()["_smtp_client"] = None
        except Exception as e:
            last_exc = e
            break

    raise RuntimeError(f"Falha ao enviar e-mail para {to_email}: {last_exc}")


def handler(event, _context):
    """
    Trigger: SQS → Records (batch).
    Estratégia: se qualquer mensagem falhar, lançamos exceção para reprocesso do batch.
    Ajuste batchSize/partial failure se quiser granularidade por mensagem.
    """
    for record in event["Records"]:
        body = record["body"]
        payload = json.loads(body) if isinstance(body, str) else body

        to_email = _resolve_email(payload)
        if not to_email:
            raise RuntimeError("Destinatário não resolvido")

        subject, text, html = _build_email(payload)
        _send_email_smtp(to_email, subject, text, html)

    return {"ok": True}
