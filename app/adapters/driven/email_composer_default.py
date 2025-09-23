from app.domain.entities import NotificationInput, Identity, EmailMessage
from app.domain.ports import EmailComposer

class DefaultEmailComposer(EmailComposer):
    def compose(self, data: NotificationInput, identity: Identity) -> EmailMessage:
        name = identity.name
        job_id = data.job_id

        if data.status == "success":
            subject = f"Seu vídeo foi processado (#{job_id})"
            link_txt = f"Link: {data.video_url}\n" if data.video_url else ""
            text = (
                f"Olá, {name}!\n\n"
                f"Seu vídeo (job {job_id}) foi processado com sucesso.\n"
                f"{link_txt}\nObrigado por usar nosso serviço."
            )
            html_link = f'<p><a href="{data.video_url}">Abrir vídeo</a></p>' if data.video_url else ""
            html = (
                f"<p>Olá, <strong>{name}</strong>!</p>"
                f"<p>Seu vídeo (job <strong>{job_id}</strong>) foi processado com sucesso.</p>"
                f"{html_link}"
                f"<p>Obrigado por usar nosso serviço.</p>"
            )
        else:
            subject = f"Falha ao processar seu vídeo (#{job_id})"
            detail = data.error_message or "não informado."
            text = (
                f"Olá, {name}!\n\n"
                f"Ocorreu um erro ao processar seu vídeo (job {job_id}).\n"
                f"Detalhes: {detail}\n\n"
                f"Tente novamente mais tarde."
            )
            html = (
                f"<p>Olá, <strong>{name}</strong>!</p>"
                f"<p><strong>Falha</strong> ao processar seu vídeo (job <strong>{job_id}</strong>).</p>"
                f"<p>Detalhes: {detail}</p>"
                f"<p>Tente novamente mais tarde.</p>"
            )

        return EmailMessage(
            to=identity.email,
            subject=subject,
            text=text.strip(),
            html=html.strip(),
        )
