from django.db import models
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel, UUIDModel
from apps.users.models import User

class Role(TimeStampedModel, UUIDModel):
    """Custom role system for granular permissions"""
    
    ROLE_TYPES = [
        ('admin', _('Administrator')),
        ('manager', _('Manager')),
        ('user', _('User')),
        ('guest', _('Guest')),
        ('custom', _('Custom')),
    ]
    
    name = models.CharField(_('Role name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True)
    role_type = models.CharField(_('Role type'), max_length=20, choices=ROLE_TYPES)
    permissions = models.ManyToManyField(Permission, blank=True, verbose_name=_('Permissions'))
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class UserRole(TimeStampedModel):
    """Association between users and roles with optional expiration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_roles')
    expires_at = models.DateTimeField(_('Expires at'), null=True, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('User Role')
        verbose_name_plural = _('User Roles')
        unique_together = ['user', 'role']
    
    def __str__(self):
        return f"{self.user} - {self.role}"

class PermissionGroup(TimeStampedModel, UUIDModel):
    """Grouping permissions for easier management"""
    name = models.CharField(_('Group name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    
    class Meta:
        verbose_name = _('Permission Group')
        verbose_name_plural = _('Permission Groups')
    
    def __str__(self):
        return self.name