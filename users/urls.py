from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='user_profile'),
    path('settings/', views.SettingsView.as_view(), name='user_settings'),
    path('sessions/', views.SessionsView.as_view(), name='user_sessions'),
    path('verify-email/<uuid:user_id>/', views.verify_email, name='verify_email'),
]