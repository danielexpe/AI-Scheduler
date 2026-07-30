# Integracao Email (Gmail SMTP)

## Configuracao (.env)

```env
GMAIL_USER=seuemail@gmail.com
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx     # Senha de aplicativo (16 digitos)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM_NAME=AI Mail Scheduler
```

---

## Como gerar o App Password no Gmail

1. Acessar: https://myaccount.google.com/security
2. Verificacao em duas etapas -> ativar (obrigatorio)
3. Voltar para Security -> "App passwords" (Senhas de aplicativo)
4. Selecionar app: "Mail", dispositivo: "Other (Custom name)" -> "AI Scheduler"
5. Copiar a senha de 16 digitos gerada (sem espacos)
6. Colar no .env como `GMAIL_APP_PASSWORD`

---

## Funcao de Envio Planejada

```python
# assinatura planejada
def send_email(
    to_email: str,
    subject: str,
    html_body: str
) -> bool:
    """
    Envia email HTML via Gmail SMTP.
    
    Args:
        to_email: Email destino
        subject: Assunto do email
        html_body: Corpo HTML completo (com CSS inline)
    
    Returns:
        True se enviado com sucesso, False caso contrario
    """
```

---

## Formato da Mensagem

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = f"{EMAIL_FROM_NAME} <{GMAIL_USER}>"
msg["To"] = to_email

html_part = MIMEText(html_body, "html", "utf-8")
msg.attach(html_part)
```

---

## Assunto do Email

Formato padrao do assunto:
```
[Scheduler] {titulo_do_prompt} - {data_atual formatada}
```

Exemplo:
```
[Scheduler] Novidades do Mercado Financeiro - 28/07/2026
```

---

## Headers SMTP

```python
with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()                    # TLS obrigatorio
    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    server.send_message(msg)
```

---

## Limites do Gmail

- **500 emails/dia** para contas gratuitas
- **2000 emails/dia** para Google Workspace
- Nossa app nao deve exceder esses limites (poucos agendamentos por dia)

---

## Tratamento de Erros SMTP

| Erro                          | Tratamento                                    |
|-------------------------------|-----------------------------------------------|
| AuthenticationError (535)     | Verificar App Password, loga erro             |
| SMTPServerDisconnected        | Retry 3x com intervalo de 10s                 |
| SMTPDataError                 | Conteudo muito grande? Loga erro              |
| Timeout                       | Retry 1x apos 30s                             |
| RecipientsRefused             | Email destino invalido, loga erro             |

---

## Validacao de Email

Antes de enviar, validar formato basico do email destino:
```python
import re
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
```

---

## Template HTML Padrao (Wrapper)

O HTML gerado pelo DeepSeek sera envolvido em um wrapper padrao:

```html
<!DOCTYPE html>
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
                    <!-- Header -->
                    <tr>
                        <td style="padding:20px; text-align:center; background-color:#16213e;">
                            <h1 style="color:#e94560; margin:0; font-size:24px;">AI Mail Scheduler</h1>
                            <p style="color:#a0a0b0; margin:5px 0 0 0; font-size:12px;">
                                Gerado em {data_hora} | Fonte: DeepSeek AI
                            </p>
                        </td>
                    </tr>
                    <!-- Content from DeepSeek -->
                    <tr>
                        <td style="padding:20px; background-color:#0f3460;">
                            {html_gerado_pelo_deepseek}
                        </td>
                    </tr>
                    <!-- Footer -->
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
</html>
```

---

## Encoding

- Sempre UTF-8
- Email header: `Content-Type: text/html; charset="utf-8"`
- MIMEText com `"html", "utf-8"`
