from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('2fa/setup/', views.setup_two_factor, name='setup_2fa'),
    path('2fa/verify/', views.verify_two_factor, name='verify_2fa'),
]