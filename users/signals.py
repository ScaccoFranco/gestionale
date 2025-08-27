from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_login_failed
from .models import User, UserProfile, UserSession, LoginAttempt

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(user_logged_in)
def create_user_session(sender, request, user, **kwargs):
    """Create session record on login"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip or '127.0.0.1'  # Fallback if no IP found
    
    ip_address = get_client_ip(request)
    session_key = request.session.session_key or 'test-session'
    
    UserSession.objects.create(
        user=user,
        session_key=session_key,
        ip_address=ip_address,
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip or '127.0.0.1'  # Fallback if no IP found
    
    email = credentials.get('username', '')
    if email:
        LoginAttempt.objects.create(
            email=email,
            ip_address=get_client_ip(request),
            success=False,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )