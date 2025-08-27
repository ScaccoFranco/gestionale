from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.users.models import User
from apps.permissions.models import Role
from .serializers import UserSerializer, RoleSerializer
from .permissions import IsAdminOrReadOnly

class UserViewSet(viewsets.ModelViewSet):
    """API ViewSet for User management"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'two_factor_enabled', 'email_verified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    @action(detail=True, methods=['post'])
    def disable_2fa(self, request, pk=None):
        """Disable 2FA for user (admin only)"""
        user = self.get_object()
        user.two_factor_enabled = False
        user.save()
        
        return Response({'message': '2FA disabled successfully'})
    
    @action(detail=True, methods=['post'])
    def reset_login_attempts(self, request, pk=None):
        """Reset failed login attempts"""
        user = self.get_object()
        user.login_attempts = 0
        user.save()
        
        return Response({'message': 'Login attempts reset'})

class RoleViewSet(viewsets.ModelViewSet):
    """API ViewSet for Role management"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role_type', 'is_active']
    search_fields = ['name', 'description']
