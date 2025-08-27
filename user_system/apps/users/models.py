from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel, UUIDModel
from cryptography.fernet import Fernet
from django.conf import settings
import os

class UserManager(BaseUserManager):
    """Custom user manager that uses email instead of username"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, TimeStampedModel, UUIDModel):
    """Custom User model with enhanced security features"""
    
    email = models.EmailField(_('Email address'), unique=True)
    first_name = models.CharField(_('First name'), max_length=150)
    last_name = models.CharField(_('Last name'), max_length=150)
    phone_number = models.CharField(_('Phone number'), max_length=20, blank=True)
    avatar = models.ImageField(_('Avatar'), upload_to='avatars/', blank=True, null=True)
    
    # Security fields
    email_verified = models.BooleanField(_('Email verified'), default=False)
    phone_verified = models.BooleanField(_('Phone verified'), default=False)
    two_factor_enabled = models.BooleanField(_('2FA Enabled'), default=False)
    login_attempts = models.IntegerField(_('Failed login attempts'), default=0)
    last_login_ip = models.GenericIPAddressField(_('Last login IP'), null=True, blank=True)
    
    # Profile fields
    timezone = models.CharField(_('Timezone'), max_length=50, default='Europe/Rome')
    language = models.CharField(_('Language'), max_length=10, default='it')
    
    # Privacy settings
    profile_public = models.BooleanField(_('Public profile'), default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        db_table = 'auth_user'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_verified_email(self):
        return self.email_verified
    
    def enable_two_factor(self):
        self.two_factor_enabled = True
        self.save(update_fields=['two_factor_enabled'])

class UserProfile(TimeStampedModel):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(_('Biography'), max_length=500, blank=True)
    birth_date = models.DateField(_('Birth date'), null=True, blank=True)
    company = models.CharField(_('Company'), max_length=100, blank=True)
    website = models.URLField(_('Website'), blank=True)
    location = models.CharField(_('Location'), max_length=100, blank=True)
    
    # Encrypted sensitive data
    encrypted_data = models.BinaryField(_('Encrypted sensitive data'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive user data"""
        if not hasattr(settings, 'ENCRYPTION_KEY'):
            settings.ENCRYPTION_KEY = Fernet.generate_key()
        
        fernet = Fernet(settings.ENCRYPTION_KEY)
        self.encrypted_data = fernet.encrypt(data.encode())
        self.save()
    
    def decrypt_sensitive_data(self):
        """Decrypt sensitive user data"""
        if not self.encrypted_data:
            return None
        
        fernet = Fernet(settings.ENCRYPTION_KEY)
        return fernet.decrypt(self.encrypted_data).decode()

class UserSession(TimeStampedModel):
    """Track user sessions for security auditing"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')

class LoginAttempt(TimeStampedModel):
    """Track login attempts for security monitoring"""
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField()
    user_agent = models.TextField()
    
    class Meta:
        verbose_name = _('Login Attempt')
        verbose_name_plural = _('Login Attempts')