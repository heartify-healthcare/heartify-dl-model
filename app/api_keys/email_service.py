"""Email service for API Key verification and notifications"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from jinja2 import Template
import os


class EmailService:
    """Handles sending emails for API key operations"""
    
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, sender_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_email = sender_email
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email with HTML content
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def send_verification_email(self, to_email: str, verification_token: str, base_url: str, action: str = "generate") -> bool:
        """
        Send email verification link
        
        Args:
            to_email: Recipient email address
            verification_token: Unique verification token
            base_url: Base URL of the application
            action: Either "generate" or "deactivate"
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'email_verification.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            print(f"Template not found: {template_path}")
            return False
        
        template = Template(template_content)
        
        # Generate verification link
        verification_link = f"{base_url}/api/v1/api-keys/verify?token={verification_token}"
        
        # Determine action text
        action_text = "API Key Generation" if action == "generate" else "API Key Deactivation"
        button_text = "Verify Email" if action == "generate" else "Confirm Deactivation"
        
        html_content = template.render(
            email=to_email,
            verification_link=verification_link,
            action_text=action_text,
            button_text=button_text
        )
        
        subject = f"Heartify - {action_text} Verification"
        
        return self._send_email(to_email, subject, html_content)
    
    def send_api_key_email(self, to_email: str, api_key: str) -> bool:
        """
        Send API key to user via email
        
        Args:
            to_email: Recipient email address
            api_key: The generated API key
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'api_key_email.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            print(f"Template not found: {template_path}")
            return False
        
        template = Template(template_content)
        
        html_content = template.render(
            email=to_email,
            api_key=api_key
        )
        
        subject = "Heartify - Your API Key"
        
        return self._send_email(to_email, subject, html_content)
    
    def send_deactivation_confirmation_email(self, to_email: str) -> bool:
        """
        Send API key deactivation confirmation
        
        Args:
            to_email: Recipient email address
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'deactivation_email.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            print(f"Template not found: {template_path}")
            return False
        
        template = Template(template_content)
        
        html_content = template.render(email=to_email)
        
        subject = "Heartify - API Key Deactivated"
        
        return self._send_email(to_email, subject, html_content)
