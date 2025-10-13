from rest_framework import serializers
from users.models import User, UserProfile
from permissions.models import Role

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'birth_date', 'company', 'website', 'location']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'avatar', 'is_active', 'is_staff',
            'email_verified', 'two_factor_enabled', 'date_joined',
            'last_login', 'profile'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

class RoleSerializer(serializers.ModelSerializer):
    permissions_count = serializers.IntegerField(source='permissions.count', read_only=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'role_type', 'is_active', 
                  'permissions', 'permissions_count', 'created_at']
        read_only_fields = ['id', 'created_at']