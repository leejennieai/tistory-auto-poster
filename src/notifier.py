"""발행 완료 이메일 알림"""

import smtplib
from email.mime.text import MIMEText


def send_notification(
    smtp_email: str,
    smtp_password: str,
    to_email: str,
    title: str,
    post_url: str = "",
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
):
    """발행 완료 알림 이메일 발송"""
    subject = f"[Tistory] {title}"
    body = f"""새 글이 발행되었습니다!

제목: {title}
링크: {post_url}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())

    print(f"[알림] 이메일 발송 완료 → {to_email}")


def send_raw_email(
    smtp_email: str,
    smtp_password: str,
    to_email: str,
    subject: str,
    body: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
):
    """범용 이메일 발송"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())
