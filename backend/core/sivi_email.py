import smtplib
from email.message import EmailMessage
import os

class JarvisEmail:
    def __init__(self):
        self.email = os.getenv("EMAIL_ADDRESS")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(self, to_address: str, subject: str, content: str) -> str:
        if not self.email or not self.password:
            return "Email credentials are not configured in the .env file."
            
        print(f" Sending email to {to_address}...")
        
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = self.email
        msg['To'] = to_address

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            return f"Email sent successfully to {to_address}."
        except Exception as e:
            print(f" Email error: {e}")
            return "Failed to send email. Please check your app password and internet connection."

email_manager = JarvisEmail()
