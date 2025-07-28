from django.urls import path
from . import views
from . import api_views  # Importa le nuove API views

urlpatterns = [
    # Pagine principali
    path('', views.home, name='home'),
    path('aziende/', views.aziende, name='aziende'),
    path('trattamenti/', views.trattamenti, name='trattamenti'),
    path('inserisci/', views.inserisci, name='inserisci'),
    path('database/', views.database, name='database'),
    
    # Pagine per gestione email
    path('contatti-email/', views.gestione_contatti_email, name='contatti_email'),
    path('comunicazioni/', views.comunicazioni_dashboard, name='comunicazioni_dashboard'),
    
    # ============ API ENDPOINTS ESISTENTI ============
    path('api/cascine/<int:cliente_id>/', views.api_cascine_by_cliente, name='api_cascine_by_cliente'),
    path('api/terreni/<int:cascina_id>/', views.api_terreni_by_cascina, name='api_terreni_by_cascina'),
    path('api/cascina/<int:cascina_id>/contoterzista/', views.api_cascina_contoterzista, name='api_cascina_contoterzista'),
    path('api/trattamenti/', views.api_create_trattamento, name='api_create_trattamento'),
    path('api/trattamenti/<int:trattamento_id>/', views.api_trattamento_detail, name='api_trattamento_detail'),
    path('api/trattamenti/<int:trattamento_id>/stato/', views.api_update_trattamento_stato, name='api_update_trattamento_stato'),
    
    # API per comunicazioni email
    path('api/trattamenti/<int:trattamento_id>/send/', views.api_send_comunicazione, name='api_send_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/preview-pdf/', views.api_preview_comunicazione, name='api_preview_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/download-pdf/', views.api_download_comunicazione, name='api_download_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/comunicazioni/', views.api_comunicazioni_trattamento, name='api_comunicazioni_trattamento'),
    
    # API per gestione contatti email esistenti
    path('api/clienti/<int:cliente_id>/contatti/', views.api_contatti_cliente, name='api_contatti_cliente'),
    path('api/clienti/<int:cliente_id>/contatti/add/', views.api_add_contatto_cliente, name='api_add_contatto_cliente'),
    path('api/contatti/<int:contatto_id>/', views.api_manage_contatto, name='api_manage_contatto'),
    
    # API di utilità esistenti
    path('api/test-email/', views.api_test_email_config, name='api_test_email_config'),
    path('api/trattamenti/communication-preview/', views.api_communication_preview, name='api_communication_preview'),
    path('api/trattamenti/bulk-action/', views.api_bulk_action_trattamenti, name='api_bulk_action_trattamenti'),

    # ============ NUOVE API PER DATABASE MANAGEMENT ============
    
    # API Clienti
    path('api/clienti/', api_views.api_clienti_list, name='api_clienti_list'),
    # path('api/clienti/create/', api_views.api_clienti_create, name='api_clienti_create'),
    
    # API Cascine  
    path('api/cascine/', api_views.api_cascine_list, name='api_cascine_list'),
    # path('api/cascine/create/', api_views.api_cascine_create, name='api_cascine_create'),
    
    # API Terreni
    path('api/terreni/', api_views.api_terreni_list, name='api_terreni_list'),
    path('api/terreni/create/', api_views.api_terreni_create, name='api_terreni_create'),
    
    # API Contoterzisti
    path('api/contoterzisti/', api_views.api_contoterzisti_list, name='api_contoterzisti_list'),
    path('api/contoterzisti/create/', api_views.api_contoterzisti_create, name='api_contoterzisti_create'),
    
    # API Prodotti
    path('api/prodotti/', api_views.api_prodotti_list, name='api_prodotti_list'),
    path('api/prodotti/create/', api_views.api_prodotti_create, name='api_prodotti_create'),
    
    # API Contatti Email (nuove - diverse da quelle esistenti)
    path('api/contatti-email/<int:cliente_id>/create/', api_views.api_contatti_email_create, name='api_contatti_email_create'),

    # API semplificate per database management
    path('api/clienti/list/', views.api_clienti_list, name='api_clienti_list'),
    path('api/clienti/create/', views.api_cliente_create, name='api_cliente_create'),
    path('api/contoterzisti/list/', views.api_contoterzisti_list, name='api_contoterzisti_list'),
    path('api/cascine/create/', views.api_cascina_create, name='api_cascina_create'),

]