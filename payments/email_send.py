"""Отправка документов на e-mail после оплаты (SMTP).

Настройки из окружения:
  SMTP_HOST, SMTP_PORT (465 SSL / 587 STARTTLS), SMTP_USER, SMTP_PASS, SMTP_FROM
"""

import os
import ssl
import smtplib
from email.message import EmailMessage


def configured():
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER"))


def send_email(to, subject, body, attachments=None):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS", "")
    sender = os.getenv("SMTP_FROM", user or "")
    if not (host and user and to):
        return False

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    for path in (attachments or []):
        try:
            with open(path, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="octet-stream",
                                   filename=os.path.basename(path))
        except Exception:
            pass

    ctx = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as s:
                s.starttls(context=ctx)
                s.login(user, pwd)
                s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001
        print("[email] ошибка отправки:", e)
        return False
