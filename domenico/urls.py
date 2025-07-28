# domenico/urls.py (aggiornato con nuove API)

from django.urls import path
from . import views

urlpatterns = [
    # Pagine principali
    path('', views.home, name='home'),
    path('aziende/', views.aziende, name='aziende'),
    path('trattamenti/', views.trattamenti, name='trattamenti'),
    path('inserisci/', views.inserisci, name='inserisci'),
    path('database/', views.database, name='database'),
    
    # Nuove pagine per gestione email
    path('contatti-email/', views.gestione_contatti_email, name='contatti_email'),
    path('comunicazioni/', views.comunicazioni_dashboard, name='comunicazioni_dashboard'),
    
    # API endpoints esistenti
    path('api/cascine/<int:cliente_id>/', views.api_cascine_by_cliente, name='api_cascine_by_cliente'),
    path('api/terreni/<int:cascina_id>/', views.api_terreni_by_cascina, name='api_terreni_by_cascina'),
    path('api/cascina/<int:cascina_id>/contoterzista/', views.api_cascina_contoterzista, name='api_cascina_contoterzista'),
    path('api/trattamenti/', views.api_create_trattamento, name='api_create_trattamento'),
    path('api/trattamenti/<int:trattamento_id>/', views.api_trattamento_detail, name='api_trattamento_detail'),
    path('api/trattamenti/<int:trattamento_id>/stato/', views.api_update_trattamento_stato, name='api_update_trattamento_stato'),
    
    # Nuove API per comunicazioni email
    path('api/trattamenti/<int:trattamento_id>/send/', views.api_send_comunicazione, name='api_send_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/preview-pdf/', views.api_preview_comunicazione, name='api_preview_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/download-pdf/', views.api_download_comunicazione, name='api_download_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/comunicazioni/', views.api_comunicazioni_trattamento, name='api_comunicazioni_trattamento'),
    
    # API per gestione contatti email
    path('api/clienti/<int:cliente_id>/contatti/', views.api_contatti_cliente, name='api_contatti_cliente'),
    path('api/clienti/<int:cliente_id>/contatti/add/', views.api_add_contatto_cliente, name='api_add_contatto_cliente'),
    path('api/contatti/<int:contatto_id>/', views.api_manage_contatto, name='api_manage_contatto'),
    
    # API di utilità
    path('api/test-email/', views.api_test_email_config, name='api_test_email_config'),
    path('api/trattamenti/communication-preview/', views.api_communication_preview, name='api_communication_preview'),

    # API bulk actions
    path('api/trattamenti/bulk-action/', views.api_bulk_action_trattamenti, name='api_bulk_action_trattamenti'),

]