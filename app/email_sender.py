import os
import re
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_gmail_user():
    return os.getenv("GMAIL_USER")


def _get_gmail_password():
    return os.getenv("GMAIL_APP_PASSWORD")


def _get_smtp_server():
    return os.getenv("SMTP_SERVER", "smtp.gmail.com")


def _get_smtp_port():
    return int(os.getenv("SMTP_PORT", "587"))


def _get_email_from_name():
    return os.getenv("EMAIL_FROM_NAME", "AI Mail Scheduler")


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


EMAIL_WRAPPER = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="margin:0; padding:0; background-color:#1a1a2e; font-family:Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a1a2e;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding:20px; text-align:center; background-color:#16213e;">
                            <h1 style="color:#e94560; margin:0; font-size:24px;">AI Mail Scheduler</h1>
                            <p style="color:#a0a0b0; margin:5px 0 0 0; font-size:12px;">
                                Gerado em {date} | Fonte: DeepSeek AI
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px; background-color:#0f3460;">
                            {body}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:15px; text-align:center; background-color:#16213e;">
                            <p style="color:#a0a0b0; font-size:11px; margin:0;">
                                Email gerado automaticamente pelo AI Mail Scheduler.
                                Para desativar, acesse a interface web.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def send_email(to_email, subject, html_body):
    gmail_user = _get_gmail_user()
    gmail_password = _get_gmail_password()
    smtp_server = _get_smtp_server()
    smtp_port = _get_smtp_port()
    email_from_name = _get_email_from_name()

    if not gmail_user or not gmail_password:
        logger.error("Credenciais Gmail nao configuradas")
        return False, "GMAIL_USER ou GMAIL_APP_PASSWORD não configurados no .env"

    if not is_valid_email(to_email):
        logger.error("Email destino invalido: %s", to_email)
        return False, f"Email destino inválido: {to_email}"

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    wrapped_html = EMAIL_WRAPPER.format(
        subject=subject,
        date=now,
        body=html_body
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{email_from_name} <{gmail_user}>"
    msg["To"] = to_email

    html_part = MIMEText(wrapped_html, "html", "utf-8")
    msg.attach(html_part)

    logger.info("Enviando email para %s (assunto: %s, body: %d chars)",
                 to_email, subject, len(html_body))

    last_error = None
    for attempt in range(3):
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(gmail_user, gmail_password)
                server.send_message(msg)
                logger.info("Email enviado com sucesso para %s (attempt %d)", to_email, attempt + 1)
                return True, None
        except smtplib.SMTPAuthenticationError:
            logger.error("Falha de autenticacao SMTP")
            return False, "Falha de autenticação SMTP. Verifique GMAIL_APP_PASSWORD."
        except smtplib.SMTPServerDisconnected:
            last_error = "Servidor SMTP desconectou"
            logger.warning("SMTP desconectou (attempt %d)", attempt + 1)
            if attempt < 2:
                import time
                time.sleep(10)
        except smtplib.SMTPDataError as e:
            logger.error("Erro de dados SMTP: %s", e)
            return False, f"Erro de dados SMTP: {e}"
        except smtplib.SMTPRecipientsRefused:
            logger.error("Email destino recusado: %s", to_email)
            return False, f"Email destino recusado: {to_email}"
        except Exception as e:
            last_error = str(e)
            logger.error("Excecao SMTP (attempt %d): %s", attempt + 1, e)
            if attempt < 2:
                import time
                time.sleep(5)

    logger.error("Todas as tentativas de envio falharam: %s", last_error)
    return False, last_error or "Erro desconhecido ao enviar email"
