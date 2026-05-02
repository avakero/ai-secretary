"""
Email Sender
Gmail SMTP 経由でレポートメールを送信する（ai-news-digest と同じ仕組み）
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


class EmailSender:
    """Gmail SMTP 経由でメール送信"""

    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 465

    def __init__(self, gmail_user: str, gmail_app_password: str):
        self.gmail_user = gmail_user
        self.gmail_app_password = gmail_app_password

    def send_html(
        self,
        recipients: list[str],
        subject: str,
        html_body: str,
        from_name: str = "📋 AI 秘書",
    ) -> bool:
        """HTML メール送信"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, self.gmail_user))
        msg["To"] = ", ".join(recipients)

        # プレーンテキストパート（HTMLが見られない環境用フォールバック）
        plain_text = "このメールは HTML 形式です。HTML を表示できる環境でご覧ください。"
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT) as server:
            server.login(self.gmail_user, self.gmail_app_password)
            server.sendmail(self.gmail_user, recipients, msg.as_string())

        return True
