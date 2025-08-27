from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Centralized email service"""
    
    @staticmethod
    def send_verification_email(user, verification_url):
        """Send email verification"""
        subject = 'Verify your email address'
        html_content = render_to_string('emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url
        })
        
        return send_mail(
            subject,
            '',  # Plain text version
            settings.EMAIL_HOST_USER,
            [user.email],
            html_message=html_content,
            fail_silently=False
        )
    
    @staticmethod
    def send_password_reset_email(user, reset_url):
        """Send password reset email"""
        subject = 'Reset your password'
        html_content = render_to_string('emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url
        })
        
        return send_mail(
            subject,
            '',
            settings.EMAIL_HOST_USER,
            [user.email],
            html_message=html_content,
            fail_silently=False
        )

class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def is_suspicious_activity(user, ip_address):
        """Check for suspicious login activity"""
        from apps.users.models import LoginAttempt
        
        # Check for multiple failed attempts
        recent_attempts = LoginAttempt.objects.filter(
            email=user.email,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        return recent_attempts > 10
    
    @staticmethod
    def log_security_event(user, event_type, details, ip_address):
        """Log security events"""
        logger.warning(f'Security event: {event_type} for user {user.email} from {ip_address}: {details}')