from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.users.models import UserProfile
from apps.permissions.models import Role

User = get_user_model()

class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123456'
        }
    
    def test_create_user(self):
        """Test user creation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data['email'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
    
    def test_create_superuser(self):
        """Test superuser creation"""
        user = User.objects.create_superuser(**self.user_data)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_user_str_method(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.first_name} {user.last_name} ({user.email})"
        self.assertEqual(str(user), expected)
    
    def test_full_name_property(self):
        """Test full_name property"""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.first_name} {user.last_name}"
        self.assertEqual(user.full_name, expected)

class AuthenticationViewTest(TestCase):
    """Test cases for authentication views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123456'
        )
        self.login_url = reverse('login')
        self.dashboard_url = reverse('dashboard')
    
    def test_login_view_get(self):
        """Test login page loads correctly"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
    
    def test_login_view_post_success(self):
        """Test successful login"""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123456'
        })
        self.assertRedirects(response, self.dashboard_url)
    
    def test_login_view_post_failure(self):
        """Test failed login"""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')

class RoleModelTest(TestCase):
    """Test cases for Role model"""
    
    def setUp(self):
        self.role_data = {
            'name': 'Test Role',
            'description': 'A test role',
            'role_type': 'custom'
        }
    
    def test_create_role(self):
        """Test role creation"""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(role.name, self.role_data['name'])
        self.assertEqual(role.role_type, self.role_data['role_type'])
        self.assertTrue(role.is_active)
    
    def test_role_str_method(self):
        """Test role string representation"""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(str(role), role.name)