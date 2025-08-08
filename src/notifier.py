import smtplib
from email.mime.text import MIMEText

class Notifier:
    def __init__(self, smtp_server, smtp_port, sender_email, receiver_email):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.receiver_email = receiver_email

    def send_email(self, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())

    def notify(self, updates):
        body = "\n".join([f"{update['actor']['login']} pushed to {update['repo']['name']}" for update in updates])
        self.send_email("GitHub Repository Updates", body)
