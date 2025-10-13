from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.http import JsonResponse
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_otp.decorators import otp_required
from django_otp.util import random_hex
from django_ratelimit.decorators import ratelimit
from axes.decorators import axes_dispatch
import json
from .serializers import UserRegistrationSerializer, LoginSerializer
from users.models import User, LoginAttempt
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
from django.contrib.auth.hashers import check_password
try:
    from qrcode import QRCode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    QRCode = None
import io
import base64


class AuthenticationView(View):
    """Base authentication view with security features"""
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_login_attempt(self, request, email, success):
        LoginAttempt.objects.create(
            email=email,
            ip_address=self.get_client_ip(request),
            success=success,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

class LoginView(AuthenticationView):
    """Enhanced login view with security features"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'authentication/login.html')
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'authentication/login.html')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                # Check if 2FA is enabled
                if user.two_factor_enabled:
                    request.session['pre_2fa_user'] = user.pk
                    return redirect('two_factor_verify')
                
                login(request, user)
                
                # Update user login info
                user.last_login_ip = self.get_client_ip(request)
                user.login_attempts = 0
                user.save(update_fields=['last_login_ip', 'login_attempts'])
                
                # Set session expiry
                if not remember_me:
                    request.session.set_expiry(0)
                
                self.log_login_attempt(request, email, True)
                
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is disabled.')
        else:
            self.log_login_attempt(request, email, False)
            messages.error(request, 'Invalid email or password.')
        
        return render(request, 'authentication/login.html')

@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', method='POST')
def api_login(request):
    """API login endpoint with JWT tokens"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(email=email, password=password)
        
        if user and user.is_active:
            if user.two_factor_enabled:
                # Return temporary token for 2FA verification
                temp_token = random_hex(32)
                request.session['temp_2fa_token'] = temp_token
                request.session['temp_2fa_user'] = user.pk
                
                return Response({
                    'requires_2fa': True,
                    'temp_token': temp_token,
                    'message': 'Please verify your 2FA code'
                })
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                }
            })
        else:
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/h', method='POST')
def register(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Send verification email
        from django.core.mail import send_mail
        from django.urls import reverse
        from django.contrib.sites.models import Site
        
        current_site = Site.objects.get_current()
        verification_url = f"http://{current_site.domain}{reverse('verify_email', args=[user.id])}"
        
        send_mail(
            'Verify your email address',
            f'Please click this link to verify your email: {verification_url}',
            'noreply@example.com',
            [user.email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'User registered successfully. Please check your email to verify your account.',
            'user_id': str(user.id)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required
def logout_view(request):
    """Secure logout with session cleanup"""
    user = request.user
    
    # Invalidate all user sessions
    from django.contrib.sessions.models import Session
    for session in Session.objects.all():
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.pk):
            session.delete()
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def setup_two_factor(request):
    """Setup TOTP 2FA for user"""
    if request.method == 'GET':
        # Generate QR code for TOTP setup
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            device = TOTPDevice.objects.create(
                user=request.user,
                name='default',
                confirmed=False
            )
        
        # Generate QR code if available
        if QRCODE_AVAILABLE:
            qr = QRCode(version=1, box_size=10, border=5)
            qr.add_data(device.config_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
        else:
            img_str = None
        
        return render(request, 'authentication/setup_2fa.html', {
            'qr_code': img_str,
            'secret_key': device.key,
            'device_id': device.id,
            'config_url': device.config_url if not QRCODE_AVAILABLE else None
        })
    
    elif request.method == 'POST':
        token = request.POST.get('token')
        device_id = request.POST.get('device_id')
        
        try:
            device = TOTPDevice.objects.get(id=device_id, user=request.user)
            if device.verify_token(token):
                device.confirmed = True
                device.save()
                
                request.user.two_factor_enabled = True
                request.user.save()
                
                messages.success(request, '2FA enabled successfully!')
                return redirect('user_profile')
            else:
                messages.error(request, 'Invalid verification code.')
        except TOTPDevice.DoesNotExist:
            messages.error(request, 'Device not found.')
        
        return redirect('setup_2fa')

@login_required 
def verify_two_factor(request):
    """Verify TOTP token during login"""
    user_id = request.session.get('pre_2fa_user')
    if not user_id:
        return redirect('login')
    
    if request.method == 'GET':
        return render(request, 'authentication/verify_2fa.html')
    
    elif request.method == 'POST':
        token = request.POST.get('token')
        
        try:
            user = User.objects.get(id=user_id)
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            
            if device and device.verify_token(token):
                login(request, user)
                del request.session['pre_2fa_user']
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid verification code.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        
        return render(request, 'authentication/verify_2fa.html')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_two_factor(request):
    """API endpoint to enable 2FA"""
    user = request.user
    
    # Create TOTP device
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if not device:
        device = TOTPDevice.objects.create(
            user=user,
            name='api-device',
            confirmed=False
        )
    
    return Response({
        'secret_key': device.key,
        'qr_code_url': device.config_url,
        'device_id': device.id
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_two_factor_api(request):
    """API endpoint to verify 2FA setup"""
    token = request.data.get('token')
    device_id = request.data.get('device_id')
    
    try:
        device = TOTPDevice.objects.get(id=device_id, user=request.user)
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            
            request.user.two_factor_enabled = True
            request.user.save()
            
            return Response({'message': '2FA enabled successfully'})
        else:
            return Response(
                {'error': 'Invalid verification code'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except TOTPDevice.DoesNotExist:
        return Response(
            {'error': 'Device not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """API endpoint to change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            {'error': 'Both old and new password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    if not check_password(old_password, user.password):
        return Response(
            {'error': 'Invalid old password'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        validate_password(new_password, user)
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})
    except ValidationError as e:
        return Response(
            {'error': e.messages}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """API endpoint for user profile management"""
    user = request.user
    
    if request.method == 'GET':
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': user.phone_number,
                'timezone': user.timezone,
                'language': user.language,
                'two_factor_enabled': user.two_factor_enabled,
                'email_verified': user.email_verified,
                'avatar': user.avatar.url if user.avatar else None,
            },
            'profile': {
                'bio': profile.bio,
                'birth_date': profile.birth_date,
                'company': profile.company,
                'website': profile.website,
                'location': profile.location,
            }
        })
    
    elif request.method == 'PUT':
        # Update user fields
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.phone_number = request.data.get('phone_number', user.phone_number)
        user.timezone = request.data.get('timezone', user.timezone)
        user.language = request.data.get('language', user.language)
        user.save()
        
        # Update profile fields
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.bio = request.data.get('bio', profile.bio)
        profile.company = request.data.get('company', profile.company)
        profile.website = request.data.get('website', profile.website)
        profile.location = request.data.get('location', profile.location)
        profile.save()
        
        return Response({'message': 'Profile updated successfully'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Logged out successfully'})
    except Exception as e:
        return Response(
            {'error': 'Invalid token'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
