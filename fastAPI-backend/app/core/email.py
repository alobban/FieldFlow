"""Email utilities and templates."""

from typing import Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, BaseLoader

from app.config import settings


# Email templates
VERIFICATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Verify Your Email</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4F46E5; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background-color: #f9fafb; }
        .button { 
            display: inline-block; 
            padding: 12px 30px; 
            background-color: #4F46E5; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px;
            margin: 20px 0;
        }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ from_name }}</h1>
        </div>
        <div class="content">
            <h2>Welcome, {{ owner_name }}!</h2>
            <p>Thank you for registering <strong>{{ organization_name }}</strong> on our platform.</p>
            <p>Please click the button below to verify your email address and continue with your tenant setup:</p>
            <p style="text-align: center;">
                <a href="{{ verification_url }}" class="button">Verify Email Address</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4F46E5;">{{ verification_url }}</p>
            <p><strong>This link will expire in {{ expire_hours }} hours.</strong></p>
            <p>If you didn't create this account, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} {{ from_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

CREDENTIAL_SETUP_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Complete Your Account Setup</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4F46E5; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background-color: #f9fafb; }
        .button { 
            display: inline-block; 
            padding: 12px 30px; 
            background-color: #10B981; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px;
            margin: 20px 0;
        }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
        .info-box { background-color: #EEF2FF; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ from_name }}</h1>
        </div>
        <div class="content">
            <h2>Email Verified Successfully!</h2>
            <p>Hi {{ owner_name }},</p>
            <p>Your email has been verified. You're almost done setting up your tenant account!</p>
            <div class="info-box">
                <strong>Your Tenant Details:</strong><br>
                Organization: {{ organization_name }}<br>
                Tenant ID: {{ tenant_name }}
            </div>
            <p>Click the button below to create your login credentials:</p>
            <p style="text-align: center;">
                <a href="{{ setup_url }}" class="button">Create Login Credentials</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #4F46E5;">{{ setup_url }}</p>
            <p><strong>This link will expire in {{ expire_hours }} hours.</strong></p>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} {{ from_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

WELCOME_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to {{ from_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4F46E5; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background-color: #f9fafb; }
        .button { 
            display: inline-block; 
            padding: 12px 30px; 
            background-color: #4F46E5; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px;
            margin: 20px 0;
        }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
        .success-box { background-color: #D1FAE5; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{ from_name }}!</h1>
        </div>
        <div class="content">
            <h2>🎉 Your Account is Ready!</h2>
            <p>Hi {{ owner_name }},</p>
            <div class="success-box">
                <strong>Congratulations!</strong> Your tenant account has been successfully created and is now active.
            </div>
            <p><strong>Your Tenant Details:</strong></p>
            <ul>
                <li>Organization: {{ organization_name }}</li>
                <li>Tenant URL Identifier: {{ tenant_name }}</li>
                <li>Admin Email: {{ email }}</li>
            </ul>
            <p>You can now log in and start using the platform:</p>
            <p style="text-align: center;">
                <a href="{{ login_url }}" class="button">Go to Login</a>
            </p>
            <p>As a tenant administrator, you can:</p>
            <ul>
                <li>Invite team members to your organization</li>
                <li>Manage user roles and permissions</li>
                <li>Configure tenant settings</li>
            </ul>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} {{ from_name }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


class EmailSender:
    """Email sender utility class."""
    
    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())
    
    def _render_template(self, template: str, context: dict) -> str:
        """Render Jinja2 template with context."""
        tmpl = self.jinja_env.from_string(template)
        return tmpl.render(**context)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """Send an email using SMTP."""
        if not settings.smtp_user or not settings.smtp_password:
            # Log warning in development
            print(f"[EMAIL] Would send to: {to_email}")
            print(f"[EMAIL] Subject: {subject}")
            print(f"[EMAIL] SMTP not configured, skipping send")
            return True
        
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.from_name} <{settings.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))
        
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=settings.smtp_tls,
            )
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        owner_name: str,
        organization_name: str,
        verification_url: str,
        expire_hours: int = 24,
    ) -> bool:
        """Send verification email to new tenant owner."""
        from datetime import datetime
        
        context = {
            "owner_name": owner_name,
            "organization_name": organization_name,
            "verification_url": verification_url,
            "expire_hours": expire_hours,
            "from_name": settings.from_name,
            "year": datetime.now().year,
        }
        
        html_content = self._render_template(VERIFICATION_EMAIL_TEMPLATE, context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Verify your email - {settings.from_name}",
            html_content=html_content,
        )
    
    async def send_credential_setup_email(
        self,
        to_email: str,
        owner_name: str,
        organization_name: str,
        tenant_name: str,
        setup_url: str,
        expire_hours: int = 24,
    ) -> bool:
        """Send credential setup email after verification."""
        from datetime import datetime
        
        context = {
            "owner_name": owner_name,
            "organization_name": organization_name,
            "tenant_name": tenant_name,
            "setup_url": setup_url,
            "expire_hours": expire_hours,
            "from_name": settings.from_name,
            "year": datetime.now().year,
        }
        
        html_content = self._render_template(CREDENTIAL_SETUP_EMAIL_TEMPLATE, context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Complete your account setup - {settings.from_name}",
            html_content=html_content,
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        owner_name: str,
        organization_name: str,
        tenant_name: str,
    ) -> bool:
        """Send welcome email after successful account setup."""
        from datetime import datetime
        
        login_url = f"{settings.frontend_url}/{tenant_name}/login"
        
        context = {
            "owner_name": owner_name,
            "organization_name": organization_name,
            "tenant_name": tenant_name,
            "email": to_email,
            "login_url": login_url,
            "from_name": settings.from_name,
            "year": datetime.now().year,
        }
        
        html_content = self._render_template(WELCOME_EMAIL_TEMPLATE, context)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.from_name}!",
            html_content=html_content,
        )


# Singleton instance
email_sender = EmailSender()