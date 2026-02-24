"""Email service for sending emails."""

from typing import Optional

from app.core.email import email_sender


class EmailService:
    """Service class for email operations."""
    
    def __init__(self):
        self.sender = email_sender
    
    async def send_verification_email(
        self,
        to_email: str,
        owner_name: str,
        organization_name: str,
        verification_url: str,
        expire_hours: int = 24,
    ) -> bool:
        """Send verification email to new tenant owner."""
        return await self.sender.send_verification_email(
            to_email=to_email,
            owner_name=owner_name,
            organization_name=organization_name,
            verification_url=verification_url,
            expire_hours=expire_hours,
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
        return await self.sender.send_credential_setup_email(
            to_email=to_email,
            owner_name=owner_name,
            organization_name=organization_name,
            tenant_name=tenant_name,
            setup_url=setup_url,
            expire_hours=expire_hours,
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        owner_name: str,
        organization_name: str,
        tenant_name: str,
    ) -> bool:
        """Send welcome email after successful account setup."""
        return await self.sender.send_welcome_email(
            to_email=to_email,
            owner_name=owner_name,
            organization_name=organization_name,
            tenant_name=tenant_name,
        )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
        expire_hours: int = 1,
    ) -> bool:
        """Send password reset email."""
        # This would use a password reset template
        # For now, using a simple email
        html_content = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hi {user_name},</p>
            <p>We received a request to reset your password. Click the link below to proceed:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in {expire_hours} hour(s).</p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
        </html>
        """
        
        return await self.sender.send_email(
            to_email=to_email,
            subject="Password Reset Request",
            html_content=html_content,
        )
    
    async def send_user_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        organization_name: str,
        invitation_url: str,
        expire_hours: int = 72,
    ) -> bool:
        """Send user invitation email."""
        html_content = f"""
        <html>
        <body>
            <h2>You've Been Invited!</h2>
            <p>Hi,</p>
            <p>{inviter_name} has invited you to join <strong>{organization_name}</strong>.</p>
            <p>Click the link below to accept the invitation and set up your account:</p>
            <p><a href="{invitation_url}">Accept Invitation</a></p>
            <p>This invitation will expire in {expire_hours} hours.</p>
        </body>
        </html>
        """
        
        return await self.sender.send_email(
            to_email=to_email,
            subject=f"You're invited to join {organization_name}",
            html_content=html_content,
        )