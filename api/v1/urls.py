from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'roles', views.RoleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('apps.authentication.api_urls')),
]