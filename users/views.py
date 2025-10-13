from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from .models import User, UserProfile, UserSession

class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard with overview"""
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        from .models import LoginAttempt
        context.update({
            'user': user,
            'recent_sessions': user.sessions.filter(is_active=True).order_by('-last_activity')[:5],
            'login_attempts': LoginAttempt.objects.filter(email=user.email).order_by('-created_at')[:10],
            'two_factor_enabled': user.two_factor_enabled,
        })
        return context

class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile management"""
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        context.update({
            'user': user,
            'profile': profile,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.save()
        
        # Update profile fields
        profile.bio = request.POST.get('bio', profile.bio)
        profile.company = request.POST.get('company', profile.company)
        profile.website = request.POST.get('website', profile.website)
        profile.location = request.POST.get('location', profile.location)
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('user_profile')

class SettingsView(LoginRequiredMixin, TemplateView):
    """User settings and preferences"""
    template_name = 'users/settings.html'
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        # Update preferences
        user.timezone = request.POST.get('timezone', user.timezone)
        user.language = request.POST.get('language', user.language)
        user.profile_public = request.POST.get('profile_public') == 'on'
        user.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('user_settings')

class SessionsView(LoginRequiredMixin, TemplateView):
    """Active sessions management"""
    template_name = 'users/sessions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'active_sessions': user.sessions.filter(is_active=True).order_by('-last_activity'),
        })
        return context

@login_required
def verify_email(request, user_id):
    """Email verification endpoint"""
    user = get_object_or_404(User, id=user_id)
    
    if user.email_verified:
        messages.info(request, 'Email already verified.')
    else:
        user.email_verified = True
        user.save()
        messages.success(request, 'Email verified successfully!')
    
    return redirect('login')