from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('login/', views.api_login, name='api_login'),
    path('register/', views.register, name='api_register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.api_logout, name='api_logout'),
    path('2fa/enable/', views.enable_two_factor, name='api_enable_2fa'),
    path('2fa/verify/', views.verify_two_factor_api, name='api_verify_2fa'),
    path('password/change/', views.change_password, name='api_change_password'),
    path('profile/', views.user_profile, name='api_user_profile'),
]