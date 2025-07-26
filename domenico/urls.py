# urls.py (app principale)
from django.urls import path
from . import views

urlpatterns = [
    # Pagine principali
    path('', views.home, name='home'),
    path('aziende/', views.aziende, name='aziende'),
    path('trattamenti/', views.trattamenti, name='trattamenti'),
    path('inserisci/', views.inserisci, name='inserisci'),
    path('database/', views.database, name='database'),
    
    # API endpoints
    path('api/cascine/<int:cliente_id>/', views.api_cascine_by_cliente, name='api_cascine_by_cliente'),
    path('api/terreni/<int:cascina_id>/', views.api_terreni_by_cascina, name='api_terreni_by_cascina'),
    path('api/cascina/<int:cascina_id>/contoterzista/', views.api_cascina_contoterzista, name='api_cascina_contoterzista'),
    path('api/trattamenti/', views.api_create_trattamento, name='api_create_trattamento'),
    path('api/trattamenti/<int:trattamento_id>/', views.api_trattamento_detail, name='api_trattamento_detail'),
    path('api/trattamenti/<int:trattamento_id>/stato/', views.api_update_trattamento_stato, name='api_update_trattamento_stato'),
]