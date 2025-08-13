# domenico/urls.py - Versione completa aggiornata

from django.urls import path
from . import views, api_views, api_communications, auth_views

auth_urlpatterns = [
    # Autenticazione
    path('login/', auth_views.custom_login, name='login'),
    path('logout/', auth_views.custom_logout, name='logout'),
    
    # Admin pannello
    path('admin-dashboard/', auth_views.admin_dashboard, name='admin_dashboard'),
    path('user-management/', auth_views.user_management, name='user_management'),
    
    # API gestione utenti
    path('api/users/create/', auth_views.api_create_user, name='api_create_user'),
    path('api/users/<int:user_id>/update/', auth_views.api_update_user, name='api_update_user'),
    path('api/users/<int:user_id>/delete/', auth_views.api_delete_user, name='api_delete_user'),
]

urlpatterns = [
    # ============ PAGINE PRINCIPALI ============
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
    path('api/trattamenti/', api_views.api_create_trattamento, name='api_create_trattamento'),
    path('api/trattamenti/<int:trattamento_id>/', views.api_trattamento_detail, name='api_trattamento_detail'),
    path('api/trattamenti/<int:trattamento_id>/stato/', views.api_update_trattamento_stato, name='api_update_trattamento_stato'),
    
    # API per comunicazioni email
    path('api/trattamenti/<int:trattamento_id>/send/', api_views.api_send_comunicazione, name='api_send_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/preview-pdf/', views.api_preview_comunicazione, name='api_preview_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/download-pdf/', views.api_download_comunicazione, name='api_download_comunicazione'),
    path('api/trattamenti/<int:trattamento_id>/comunicazioni/', views.api_comunicazioni_trattamento, name='api_comunicazioni_trattamento'),
    
    # API per gestione contatti email esistenti
    path('api/clienti/<int:cliente_id>/contatti/', views.api_contatti_cliente, name='api_contatti_cliente'),
    path('api/clienti/<int:cliente_id>/contatti/add/', api_views.api_add_contatto_cliente, name='api_add_contatto_cliente'),
    path('api/contatti/<int:contatto_id>/', views.api_manage_contatto, name='api_manage_contatto'),
    
    # API di utilità esistenti
    path('api/test-email/', views.api_test_email_config, name='api_test_email_config'),
    path('api/trattamenti/bulk-action/', views.api_bulk_action_trattamenti, name='api_bulk_action_trattamenti'),

    # ============ NUOVE API PER DATABASE MANAGEMENT ============
    
    # API Cascine  
    path('api/cascine/', api_views.api_cascine_list, name='api_cascine_list'),
    path('api/cascine/create/', api_views.api_cascine_create, name='api_cascine_create'),
    
    # API Terreni
    path('api/terreni/', api_views.api_terreni_list, name='api_terreni_list'),
    path('api/terreni/create/', api_views.api_terreni_create, name='api_terreni_create'),
    
    # API Prodotti
    path('api/prodotti/create/', api_views.api_prodotti_create, name='api_prodotti_create'),
    path('api/principi-attivi/', api_views.api_principi_attivi_list, name='api_principi_attivi_list'),
    
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
    path('api/clienti/create/', api_views.api_cliente_create, name='api_cliente_create'),
    path('api/contoterzisti/create/', views.api_contoterzista_create, name='api_contoterzista_create'),
    path('api/contoterzisti/list/', views.api_contoterzisti_list, name='api_contoterzisti_list'),

    # API per selezione dinamica trattamenti
    path('api/clienti/', api_views.api_clienti, name='api_clienti'),
    path('api/clienti/<int:cliente_id>/cascine/', api_views.api_cliente_cascine, name='api_cliente_cascine'),
    path('api/cascine/<int:cascina_id>/terreni/', api_views.api_cascina_terreni, name='api_cascina_terreni'),
    path('api/search/clienti/', api_views.api_search_clienti, name='api_search_clienti'),

    
    # ============ NUOVE API PER ATTIVITÀ E DASHBOARD ============
    
    # API Attività Recenti
    path('api/recent-activities/', api_views.api_recent_activities, name='api_recent_activities'),
    path('api/dashboard/summary/', api_views.api_dashboard_summary, name='api_dashboard_summary'),
    
    # API Statistiche Database
    path('api/database/stats/', api_views.api_database_stats, name='api_database_stats'),

   # API Meteo - Endpoint principali
    path('api/weather/current/', views.api_weather_current, name='api_weather_current'),
    # path('api/weather/test/', views.api_weather_test, name='api_weather_test'),       DA INSERIRE
    
    # API Meteo - Debug e gestione cache
    path('api/weather/clear-cache/', views.api_weather_clear_cache, name='api_weather_clear_cache'),
    path('api/weather/debug-cache/', views.api_weather_debug_cache, name='api_weather_debug_cache'),
    path('api/weather/location-test/', views.api_weather_location_test, name='api_weather_location_test'),
    path('api/weather/debug/<str:location>/', views.api_weather_debug_location, name='api_weather_debug_location'),


        # === NUOVE URL PER INTERFACCIA AZIENDE ===
    
    # Navigazione gerarchica
    path('aziende/<int:cliente_id>/cascine/', views.aziende_cascine, name='aziende_cascine'),
    path('aziende/cascine/<int:cascina_id>/terreni/', views.aziende_terreni, name='aziende_terreni'),
    
    # Modifica elementi
    path('aziende/edit/cliente/<int:cliente_id>/', views.edit_cliente, name='edit_cliente'),
    path('aziende/edit/cascina/<int:cascina_id>/', views.edit_cascina, name='edit_cascina'),
    path('aziende/edit/terreno/<int:terreno_id>/', views.edit_terreno, name='edit_terreno'),

    # Aggiungi questi path
    path('comunicazione-wizard/', views.comunicazione_wizard, name='comunicazione_wizard'),
    path('api/trattamenti/generate-company-pdf/', api_communications.api_generate_company_pdf, name='api_generate_company_pdf'),

    path('api/trattamenti/communication-status/', views.api_communication_status_check, name='api_communication_status'),
    path('api/trattamenti/communication-preview/', api_communications.api_communication_preview, name='api_communication_preview'),
] + auth_urlpatterns