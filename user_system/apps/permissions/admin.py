from django.contrib import admin
from .models import Role, UserRole, PermissionGroup

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'role_type', 'is_active', 'created_at')
    list_filter = ('role_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_by', 'expires_at', 'is_active')
    list_filter = ('role', 'is_active', 'expires_at', 'created_at')
    search_fields = ('user__email', 'role__name')

@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)