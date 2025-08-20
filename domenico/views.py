from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.conf import settings 
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json
from .models import *
from .weather_service import weather_service
import logging
from django.contrib import messages
from django.urls import reverse
from django.template.loader import render_to_string
from decimal import Decimal
import io
from django.http import HttpResponse


# Import delle funzioni email
from .email_utils import (
    send_trattamento_communication, 
    preview_comunicazione_pdf, 
    download_comunicazione_pdf,
    get_contatti_by_cliente,
    add_contatto_email,
    update_contatto_email,
    delete_contatto_email,
    test_email_configuration,
    get_comunicazioni_stats
)


def public_landing(request):
    """Vista landing page pubblica per utenti non autenticati"""
    return render(request, 'public_landing.html')

def personal_dashboard(request):
    """Vista dashboard personale per utenti autenticati"""
    from django.db.models import Sum, Count, Q
    from datetime import datetime, timedelta
    
    # Calcola statistiche
    stats = {
        'clienti_totali': Cliente.objects.count(),
        'cascine_totali': Cascina.objects.count(),
        'terreni_totali': Terreno.objects.count(),
        'superficie_totale': Terreno.objects.aggregate(
            totale=Sum('superficie')
        )['totale'] or 0,
        'trattamenti_programmati': Trattamento.objects.filter(stato='programmato').count(),
        'trattamenti_completati': Trattamento.objects.filter(stato='completato').count(),
    }
    
    # Attività recenti (ultimi 30 giorni)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_activities = ActivityLog.objects.filter(
        timestamp__gte=thirty_days_ago
    ).order_by('-timestamp')[:10]
    
    # Trattamenti recenti
    recent_treatments = Trattamento.objects.select_related(
        'cliente', 'cascina'
    ).prefetch_related('terreni').order_by('-data_inserimento')[:5]
    
    # Dati per grafici (ultimi 12 mesi)
    monthly_data = []
    for i in range(12):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_treatments = Trattamento.objects.filter(
            data_inserimento__year=month_start.year,
            data_inserimento__month=month_start.month
        ).count()
        monthly_data.append({
            'month': month_start.strftime('%b'),
            'treatments': month_treatments
        })
    monthly_data.reverse()
    
    context = {
        'stats': stats,
        'recent_activities': recent_activities,
        'recent_treatments': recent_treatments,
        'monthly_data': monthly_data,
        'user': request.user,
    }
    
    return render(request, 'personal_dashboard.html', context)

def home(request):
    """Vista home che reindirizza alla landing page o dashboard personale"""
    if request.user.is_authenticated:
        return personal_dashboard(request)
    else:
        return public_landing(request)

def offline_page(request):
    """Pagina offline per PWA"""
    return render(request, 'offline.html')

def legacy_home(request):
    """Vista home originale con statistiche e attività recenti dal database management (deprecated)"""
    from django.db.models import Sum, Count, Q
    from datetime import datetime, timedelta
    
    # Calcola statistiche
    stats = {
        'clienti_totali': Cliente.objects.count(),
        'cascine_totali': Cascina.objects.count(),
        'terreni_totali': Terreno.objects.count(),
        'superficie_totale': Terreno.objects.aggregate(
            totale=Sum('superficie')
        )['totale'] or 0,
        'trattamenti_programmati': Trattamento.objects.filter(stato='programmato').count(),
        'trattamenti_comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'prodotti_totali': Prodotto.objects.count(),
        'contoterzisti_totali': Contoterzista.objects.count(),
    }
    
    # Attività recenti (ultimi 10 giorni, massimo 15 attività)
    dieci_giorni_fa = timezone.now() - timedelta(days=10)
    
    attivita_recenti = ActivityLog.objects.filter(
        timestamp__gte=dieci_giorni_fa
    ).select_related().order_by('-timestamp')[:15]
    
    # Trattamenti recenti (per compatibilità con template esistente)
    trattamenti_recenti = Trattamento.objects.select_related(
        'cliente', 'cascina'
    ).prefetch_related('terreni')[:5]
    
    # Statistiche attività per tipo (per dashboard)
    activity_stats = {}
    if attivita_recenti.exists():
        from django.db.models import Count
        activity_stats = ActivityLog.objects.filter(
            timestamp__gte=dieci_giorni_fa
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
    
    # Attività di oggi
    oggi_inizio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    attivita_oggi = ActivityLog.objects.filter(
        timestamp__gte=oggi_inizio
    ).count()
    
    context = {
        'stats': stats,
        'trattamenti_recenti': trattamenti_recenti,  # Per compatibilità
        'attivita_recenti': attivita_recenti,  # 🔥 NUOVO
        'activity_stats': activity_stats,  # 🔥 NUOVO
        'attivita_oggi': attivita_oggi,  # 🔥 NUOVO
    }
    
    return render(request, 'home.html', context)

def aziende(request):
    """Vista aziende con ricerca e ordinamento case-insensitive"""
    from django.db.models import Sum, Count, Q
    from django.db.models.functions import Lower
    
    # Parametro di ricerca
    search_query = request.GET.get('search', '').strip()
    
    # Carica tutti i clienti con le relazioni necessarie
    clienti = Cliente.objects.prefetch_related(
        'cascine__terreni',
        'cascine__contoterzista',
        'trattamenti'
    ).annotate(
        superficie_totale=Sum('cascine__terreni__superficie'),
        trattamenti_programmati=Count(
            'trattamenti', 
            filter=Q(trattamenti__stato='programmato')
        ),
        trattamenti_comunicati=Count(
            'trattamenti', 
            filter=Q(trattamenti__stato='comunicato')
        )
    )
    
    # Applica filtro di ricerca se presente
    if search_query:
        clienti = clienti.filter(
            nome__icontains=search_query
        )
    
    # Ordinamento case-insensitive
    clienti = clienti.order_by(Lower('nome'))
    
    # Costruisci la struttura ad albero
    aziende_tree = []
    for cliente in clienti:
        cliente_data = {
            'id': cliente.id,
            'nome': cliente.nome,
            'superficie_totale': cliente.superficie_totale or 0,
            'trattamenti_programmati': cliente.trattamenti_programmati,
            'trattamenti_comunicati': cliente.trattamenti_comunicati,
            'cascine': []
        }
        
        # Ordina cascine case-insensitive
        cascine_ordinate = cliente.cascine.all().order_by(Lower('nome'))
        
        for cascina in cascine_ordinate:
            superficie_cascina = sum(terreno.superficie for terreno in cascina.terreni.all())
            
            cascina_data = {
                'id': cascina.id,
                'nome': cascina.nome,
                'superficie_totale': superficie_cascina,
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'contoterzista_id': cascina.contoterzista.id if cascina.contoterzista else None,
                'trattamenti_programmati': 0,  # Calcolo semplificato
                'trattamenti_comunicati': 0,   # Calcolo semplificato
                'terreni': list(cascina.terreni.all().order_by(Lower('nome')))
            }
            
            cliente_data['cascine'].append(cascina_data)
        
        aziende_tree.append(cliente_data)
    
    context = {
        'aziende_tree': aziende_tree,
        'search_query': search_query,
        'total_count': len(aziende_tree)
    }
    
    return render(request, 'aziende.html', context)

def trattamenti(request):
    """Vista principale trattamenti"""
    view_type = request.GET.get('view', 'dashboard')
    
    if view_type == 'dashboard':
        return trattamenti_dashboard(request)
    else:
        return trattamenti_table(request, view_type)

def trattamenti_dashboard(request):
    """Dashboard trattamenti con statistiche (senza in_esecuzione)"""
    from django.db.models import Count
    
    # Calcola statistiche (rimosso in_esecuzione)
    stats = {
        'totali': Trattamento.objects.count(),
        'programmati': Trattamento.objects.filter(stato='programmato').count(),
        'comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'completati': Trattamento.objects.filter(stato='completato').count(),
        'annullati': Trattamento.objects.filter(stato='annullato').count(),
    }
    
    # Trattamenti recenti
    trattamenti_recenti = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni')[:10]
    
    context = {
        'stats': stats,
        'trattamenti_recenti': trattamenti_recenti,
    }
    
    return render(request, 'trattamenti.html', context)

def trattamenti_table(request, view_type):
    """Vista tabella trattamenti con filtri (senza in_esecuzione)"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Query base
    trattamenti = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni', 'trattamentoprodotto_set__prodotto')
    
    # Mappatura corretta degli stati (rimosso in_esecuzione)
    stati_mapping = {
        'programmati': 'programmato',
        'comunicati': 'comunicato', 
        'completati': 'completato',
        'annullati': 'annullato'
    }
    
    # Filtri per stato
    if view_type in stati_mapping:
        stato_db = stati_mapping[view_type]
        trattamenti = trattamenti.filter(stato=stato_db)
        print(f"Filtrando per stato: {view_type} -> {stato_db}")
        print(f"Trattamenti trovati: {trattamenti.count()}")
    elif view_type != 'tutti':
        print(f"Tipo vista non riconosciuto: {view_type}")
    
    # Filtri dalla query string
    filters = {
        'search': request.GET.get('search', ''),
        'cliente': request.GET.get('cliente', ''),
        'cascina': request.GET.get('cascina', ''),
        'contoterzista': request.GET.get('contoterzista', ''),
    }
    
    # Applica filtri
    if filters['search']:
        trattamenti = trattamenti.filter(
            Q(cliente__nome__icontains=filters['search']) |
            Q(cascina__nome__icontains=filters['search']) |
            Q(id__icontains=filters['search'])
        )
    
    if filters['cliente']:
        trattamenti = trattamenti.filter(cliente_id=filters['cliente'])
    
    if filters['cascina']:
        trattamenti = trattamenti.filter(cascina_id=filters['cascina'])
    
    if filters['contoterzista']:
        trattamenti = trattamenti.filter(cascina__contoterzista_id=filters['contoterzista'])
    
    # Ordinamento
    trattamenti = trattamenti.order_by('-data_inserimento')
    
    # Paginazione
    paginator = Paginator(trattamenti, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche per la vista (senza in_esecuzione)
    stats = {
        'totali': Trattamento.objects.count(),
        'filtrati': trattamenti.count(),
        'programmati': Trattamento.objects.filter(stato='programmato').count(),
        'comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'completati': Trattamento.objects.filter(stato='completato').count(),
    }
    
    # Dati per i dropdown
    clienti = Cliente.objects.all().order_by('nome')
    cascine = Cascina.objects.select_related('cliente').order_by('nome')
    contoterzisti = Contoterzista.objects.all().order_by('nome')
    
    # Titoli e descrizioni per vista (aggiornati)
    view_info = {
        'tutti': {
            'title': 'Tutti i Trattamenti',
            'description': 'Elenco completo di tutti i trattamenti registrati nel sistema',
            'next_action': None
        },
        'programmati': {
            'title': 'Trattamenti Programmati',
            'description': 'Trattamenti pianificati che necessitano di essere comunicati',
            'next_action': 'comunica'
        },
        'comunicati': {
            'title': 'Trattamenti Comunicati',
            'description': 'Trattamenti comunicati ai contoterzisti e pronti per l\'esecuzione',
            'next_action': 'completa'
        },
        'completati': {
            'title': 'Trattamenti Completati',
            'description': 'Trattamenti eseguiti con successo',
            'next_action': None
        },
        'annullati': {
            'title': 'Trattamenti Annullati',
            'description': 'Trattamenti cancellati o non eseguiti',
            'next_action': None
        }
    }
    
    current_view = view_info.get(view_type, view_info['tutti'])
    
    context = {
        'trattamenti': page_obj,
        'page_obj': page_obj,  # Aggiunto per la paginazione
        'is_paginated': page_obj.has_other_pages(),  # Aggiunto per la paginazione
        'stats': stats,
        'filters': filters,
        'clienti': clienti,
        'cascine': cascine,
        'contoterzisti': contoterzisti,
        'view_type': view_type,  # ✅ IMPORTANTE: Assicurati che sia sempre presente
        'view_title': current_view['title'],
        'view_description': current_view['description'],
        'next_action': current_view['next_action'],
    }
    
    return render(request, 'trattamenti_table.html', context)

def inserisci(request):
    """Vista per inserire nuovo trattamento"""
    clienti = Cliente.objects.all().order_by('nome')
    prodotti = Prodotto.objects.all().order_by('nome')
    
    context = {
        'clienti': clienti,
        'prodotti': prodotti,
    }
    
    return render(request, 'inserisci.html', context)

def database(request):
    """Vista gestione database"""
    # Statistiche per la dashboard
    stats = {
        'clienti': Cliente.objects.count(),
        'cascine': Cascina.objects.count(),
        'terreni': Terreno.objects.count(),
        'contoterzisti': Contoterzista.objects.count(),
        'prodotti': Prodotto.objects.count(),
        'trattamenti': Trattamento.objects.count(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'database.html', context)



def gestione_contatti_email(request):
    """Vista per gestire i contatti email dei clienti"""
    from django.db.models import Count
    
    # Ottieni tutti i clienti con il numero di contatti
    clienti = Cliente.objects.annotate(
        contatti_count=Count('contatti_email'),
    ).order_by('nome')
    
    # Statistiche generali
    stats = {
        'clienti_totali': clienti.count(),
        'clienti_con_contatti': clienti.filter(contatti_count__gt=0).count(),
        'contatti_totali': ContattoEmail.objects.count(),
    }
    
    context = {
        'clienti': clienti,
        'stats': stats,
    }
    
    return render(request, 'gestione_contatti_email.html', context)


def comunicazioni_dashboard(request):
    """Dashboard per visualizzare lo storico delle comunicazioni"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from datetime import datetime
    
    # Filtri
    cliente_filter = request.GET.get('cliente', '')
    data_da = request.GET.get('data_da', '')
    data_a = request.GET.get('data_a', '')
    solo_errori = request.GET.get('solo_errori', False)
    
    # Query base
    comunicazioni = ComunicazioneTrattamento.objects.select_related(
        'trattamento__cliente', 'trattamento__cascina'
    ).order_by('-data_invio')
    
    # Applica filtri
    if cliente_filter:
        comunicazioni = comunicazioni.filter(trattamento__cliente_id=cliente_filter)
    
    if data_da and data_a:
        try:
            data_da_obj = datetime.strptime(data_da, '%Y-%m-%d').date()
            data_a_obj = datetime.strptime(data_a, '%Y-%m-%d').date()
            comunicazioni = comunicazioni.filter(
                data_invio__date__gte=data_da_obj,
                data_invio__date__lte=data_a_obj
            )
        except ValueError:
            pass
    
    if solo_errori:
        comunicazioni = comunicazioni.filter(inviato_con_successo=False)
    
    # Paginazione
    paginator = Paginator(comunicazioni, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche
    from .email_utils import get_comunicazioni_stats
    try:
        stats = get_comunicazioni_stats()
    except:
        stats = {
            'totali': comunicazioni.count(),
            'riuscite': comunicazioni.filter(inviato_con_successo=True).count(),
            'fallite': comunicazioni.filter(inviato_con_successo=False).count(),
            'oggi': 0,
            'questa_settimana': 0,
            'questo_mese': 0,
        }
    
    # Clienti per il filtro
    clienti = Cliente.objects.all().order_by('nome')
    
    context = {
        'comunicazioni': page_obj,
        'stats': stats,
        'clienti': clienti,
        'filters': {
            'cliente': cliente_filter,
            'data_da': data_da,
            'data_a': data_a,
            'solo_errori': solo_errori,
        }
    }
    
    return render(request, 'comunicazioni_dashboard.html', context)

# ============ API ENDPOINTS per COMUNICAZIONI EMAIL ============

@require_http_methods(["GET", "POST", "DELETE"])
def api_manage_contatto(request, contatto_id):
    """API per gestire un contatto email (GET, POST per modifica, DELETE)"""
    try:
        contatto = get_object_or_404(ContattoEmail, id=contatto_id)
        
        if request.method == 'GET':
            # Restituisce i dati del contatto per la modifica
            return JsonResponse({
                'success': True,
                'contatto': {
                    'id': contatto.id,
                    'nome': contatto.nome,
                    'email': contatto.email,
                    'cliente_id': contatto.cliente.id,
                    'cliente_nome': contatto.cliente.nome
                }
            })
            
        elif request.method == 'POST':
            # Modifica il contatto esistente
            nome = request.POST.get('nome', '').strip()
            email = request.POST.get('email', '').strip()
            
            if not nome:
                return JsonResponse({
                    'success': False,
                    'error': 'Il nome è obbligatorio'
                }, status=400)
                
            if not email:
                return JsonResponse({
                    'success': False,
                    'error': 'L\'email è obbligatoria'
                }, status=400)
            
            # Validazione email
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email):
                return JsonResponse({
                    'success': False,
                    'error': 'Indirizzo email non valido'
                }, status=400)
            
            # Verifica che non esista già un altro contatto con la stessa email per lo stesso cliente
            conflitto = ContattoEmail.objects.filter(
                cliente=contatto.cliente, 
                email__iexact=email
            ).exclude(id=contatto.id).first()
            
            if conflitto:
                return JsonResponse({
                    'success': False,
                    'error': f'Esiste già un contatto con l\'email "{email}" per questo cliente'
                }, status=400)
            
            # Aggiorna i campi
            contatto.nome = nome
            contatto.email = email
            
            contatto.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Contatto {contatto.nome} aggiornato con successo',
                'contatto': {
                    'id': contatto.id,
                    'nome': contatto.nome,
                    'email': contatto.email,
                }
            })
            
        elif request.method == 'DELETE':
            # Elimina il contatto
            nome_contatto = contatto.nome
            cliente_nome = contatto.cliente.nome
            contatto.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Contatto {nome_contatto} eliminato con successo da {cliente_nome}'
            })
            
    except ContattoEmail.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Contatto non trovato'
        }, status=404)
    except Exception as e:
        print(f"Errore in api_manage_contatto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'operazione: {str(e)}'
        }, status=500)


def api_comunicazioni_trattamento(request, trattamento_id):
    """API per ottenere lo storico delle comunicazioni di un trattamento"""
    try:
        trattamento = get_object_or_404(Trattamento, id=trattamento_id)
        comunicazioni = trattamento.comunicazioni.all().order_by('-data_invio')
        
        comunicazioni_data = []
        for comunicazione in comunicazioni:
            comunicazioni_data.append({
                'id': comunicazione.id,
                'data_invio': comunicazione.data_invio.isoformat(),
                'destinatari': comunicazione.destinatari.split(', '),
                'oggetto': comunicazione.oggetto,
                'inviato_con_successo': comunicazione.inviato_con_successo,
                'errore': comunicazione.errore,
                'allegati': comunicazione.allegati.split(', ') if comunicazione.allegati else []
            })
        
        return JsonResponse({
            'success': True,
            'comunicazioni': comunicazioni_data,
            'count': len(comunicazioni_data),
            'trattamento': {
                'id': trattamento.id,
                'cliente': trattamento.cliente.nome,
                'stato': trattamento.stato,
                'stato_display': trattamento.get_stato_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def api_test_email_config(request):
    """API per testare la configurazione email"""
    try:
        risultato = test_email_configuration()
        
        if risultato['success']:
            return JsonResponse(risultato)
        else:
            return JsonResponse(risultato, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore nel test email: {str(e)}'
        }, status=500)

# ============ VIEWS PER GESTIONE CONTATTI EMAIL ============

# ============ AGGIORNAMENTO API TRATTAMENTI ============

def api_trattamento_detail(request, trattamento_id):
    """API per ottenere i dettagli di un trattamento con quantità per ettaro"""
    try:
        trattamento = get_object_or_404(
            Trattamento.objects.select_related(
                'cliente', 'cascina', 'cascina__contoterzista'
            ).prefetch_related('terreni', 'prodotti'),
            id=trattamento_id
        )
        
        # Serializza i dati
        data = {
            'id': trattamento.id,
            'cliente': {
                'id': trattamento.cliente.id,
                'nome': trattamento.cliente.nome
            },
            'cascina': {
                'id': trattamento.cascina.id,
                'nome': trattamento.cascina.nome,
                'contoterzista': {
                    'id': trattamento.cascina.contoterzista.id,
                    'nome': trattamento.cascina.contoterzista.nome
                } if trattamento.cascina.contoterzista else None
            } if trattamento.cascina else None,
            'terreni': [
                {
                    'id': t.id,
                    'nome': t.nome,
                    'superficie': float(t.superficie)
                } for t in trattamento.terreni.all()
            ],
            'contoterzista': {
                'id': trattamento.get_contoterzista().id,
                'nome': trattamento.get_contoterzista().nome
            } if trattamento.get_contoterzista() else None,
            'stato': trattamento.stato,
            'stato_display': trattamento.get_stato_display(),
            'livello_applicazione': trattamento.livello_applicazione,
            'superficie_interessata': float(trattamento.get_superficie_interessata()),
            'data_inserimento': trattamento.data_inserimento.isoformat(),
            'data_comunicazione': trattamento.data_comunicazione.isoformat() if trattamento.data_comunicazione else None,
            'data_esecuzione': trattamento.data_esecuzione.isoformat() if trattamento.data_esecuzione else None,
            'prodotti': [
                {
                    'nome': tp.prodotto.nome,
                    'quantita_per_ettaro': float(tp.quantita_per_ettaro),
                    'quantita_totale': float(tp.quantita_totale),
                    'unita_misura': tp.prodotto.unita_misura
                } for tp in trattamento.trattamentoprodotto_set.all()
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ============ RESTO DELLE VIEWS ESISTENTI ============
# (home, aziende, trattamenti, ecc. rimangono invariate) e:

def api_preview_comunicazione(request, trattamento_id):
    """API per visualizzare l'anteprima PDF della comunicazione"""
    return preview_comunicazione_pdf(request, trattamento_id)

def api_download_comunicazione(request, trattamento_id):
    """API per scaricare il PDF della comunicazione"""
    return download_comunicazione_pdf(request, trattamento_id)

def api_contatti_cliente(request, cliente_id):
    """API per ottenere i contatti email di un cliente"""
    try:
        contatti = get_contatti_by_cliente(cliente_id)
        
        if contatti is None:
            return JsonResponse({
                'success': False,
                'error': 'Cliente non trovato'
            }, status=404)
        
        contatti_data = []
        for contatto in contatti:
            contatti_data.append({
                'id': contatto.id,
                'nome': contatto.nome,
                'email': contatto.email,
            })
        
        return JsonResponse({
            'success': True,
            'contatti': contatti_data,
            'count': len(contatti_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
def api_cascine_by_cliente(request, cliente_id):
    """API per ottenere le cascine di un cliente"""
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        cascine = cliente.cascine.select_related('contoterzista').prefetch_related('terreni')
        
        cascine_data = []
        for cascina in cascine:
            superficie_totale = sum(terreno.superficie for terreno in cascina.terreni.all())
            
            cascine_data.append({
                'id': cascina.id,
                'nome': cascina.nome,
                'superficie_totale': float(superficie_totale),
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'terreni_count': cascina.terreni.count()
            })
        
        return JsonResponse(cascine_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_terreni_by_cascina(request, cascina_id):
    """API per ottenere i terreni di una cascina"""
    try:
        cascina = get_object_or_404(Cascina, id=cascina_id)
        terreni = cascina.terreni.all()
        
        terreni_data = []
        for terreno in terreni:
            terreni_data.append({
                'id': terreno.id,
                'nome': terreno.nome,
                'superficie': float(terreno.superficie),
                'cascina_nome': cascina.nome,
                'cascina_id': cascina.id
            })
        
        return JsonResponse(terreni_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_cascina_contoterzista(request, cascina_id):
    """API per ottenere il contoterzista di una cascina"""
    try:
        cascina = get_object_or_404(Cascina, id=cascina_id)
        
        if cascina.contoterzista:
            return JsonResponse({
                'contoterzista': {
                    'id': cascina.contoterzista.id,
                    'nome': cascina.contoterzista.nome,
                    'email': cascina.contoterzista.email,
                }
            })
        else:
            return JsonResponse({'contoterzista': None})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_update_trattamento_stato(request, trattamento_id):
    """API per aggiornare lo stato di un trattamento"""
    try:
        trattamento = get_object_or_404(Trattamento, id=trattamento_id)
        nuovo_stato = request.POST.get('stato')
        
        if nuovo_stato not in dict(Trattamento.STATI_CHOICES):
            return JsonResponse({
                'success': False,
                'error': 'Stato non valido'
            }, status=400)
        
        stato_precedente = trattamento.stato
        trattamento.stato = nuovo_stato
        trattamento.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Stato aggiornato da "{trattamento.get_stato_display()}" a "{nuovo_stato}"',
            'stato_precedente': stato_precedente,
            'nuovo_stato': nuovo_stato
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'aggiornamento: {str(e)}'
        }, status=500)

# Aggiungi anche questa nuova API per la generazione PDF:
@csrf_exempt
@require_http_methods(["POST"])
def api_generate_company_pdf(request):
    """
    API per generare un PDF di comunicazione per una specifica azienda
    con tutti i suoi trattamenti e note personalizzate
    """
    try:
        print(f"🔍 DEBUG PDF: Content-Type: {request.content_type}")
        
        # Gestisce sia JSON che FormData
        if request.content_type and 'application/json' in request.content_type:
            import json
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = dict(request.POST)
            # Converte liste a valori singoli se necessario
            for key, value in data.items():
                if isinstance(value, list) and len(value) == 1:
                    data[key] = value[0]
        
        trattamenti_ids = data.get('trattamenti_ids', [])
        company_name = data.get('company_name', '')
        custom_notes = data.get('custom_notes', '')
        update_status = data.get('update_status', True)
        
        print(f"🔍 DEBUG PDF: trattamenti_ids={trattamenti_ids}, company={company_name}")
        
        if not trattamenti_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento specificato'
            }, status=400)
        
        # Recupera i trattamenti
        trattamenti = Trattamento.objects.filter(
            id__in=trattamenti_ids
        ).select_related(
            'cliente', 'cascina'
        ).prefetch_related(
            'terreni', 'trattamentoprodotto_set__prodotto'
        )
        
        if not trattamenti.exists():
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento trovato'
            }, status=404)
        
        # Verifica che tutti i trattamenti appartengano alla stessa azienda
        cliente = trattamenti.first().cliente
        if not all(t.cliente == cliente for t in trattamenti):
            return JsonResponse({
                'success': False,
                'error': 'Tutti i trattamenti devono appartenere alla stessa azienda'
            }, status=400)
        
        # Genera il PDF
        try:
            pdf_content = generate_company_communication_pdf(trattamenti, custom_notes)
            print(f"🔍 DEBUG PDF: Generato PDF di {len(pdf_content)} bytes")
        except Exception as e:
            print(f"❌ DEBUG PDF: Errore generazione: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Errore nella generazione del PDF: {str(e)}'
            }, status=500)
        
        # Aggiorna lo stato dei trattamenti se richiesto
        if update_status:
            with transaction.atomic():
                for trattamento in trattamenti:
                    if trattamento.stato == 'programmato':
                        trattamento.stato = 'comunicato'
                        trattamento.data_comunicazione = timezone.now()
                        trattamento.save()
                        print(f"🔍 DEBUG PDF: Aggiornato stato trattamento {trattamento.id}")
        
        # Prepara la risposta HTTP con il PDF
        filename = f"Comunicazione_{company_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        print(f"🔍 DEBUG PDF: Risposta preparata con filename: {filename}")
        return response
        
    except json.JSONDecodeError as e:
        print(f"❌ DEBUG PDF: Errore JSON: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Formato JSON non valido: {str(e)}'
        }, status=400)
    except Exception as e:
        print(f"❌ DEBUG PDF: Errore generale: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la generazione del PDF: {str(e)}'
        }, status=500)


def generate_company_communication_pdf(trattamenti, custom_notes=''):
    """
    Genera un PDF di comunicazione per un'azienda con tutti i suoi trattamenti
    """
    try:
        print(f"🔍 DEBUG PDF Generator: Inizio generazione per {len(trattamenti)} trattamenti")
        
        # Import per PDF (prova prima WeasyPrint, poi xhtml2pdf)
        pdf_engine = None
        try:
            from weasyprint import HTML, CSS
            pdf_engine = 'weasyprint'
            print("🔍 DEBUG PDF: Usando WeasyPrint")
        except ImportError:
            try:
                from xhtml2pdf import pisa
                pdf_engine = 'xhtml2pdf'
                print("🔍 DEBUG PDF: Usando xhtml2pdf")
            except ImportError:
                raise Exception("Nessun motore PDF disponibile. Installa WeasyPrint o xhtml2pdf.")
        
        # Prepara i dati per il template
        cliente = trattamenti.first().cliente
        
        # Calcola totali
        superficie_totale = sum(float(t.get_superficie_interessata()) for t in trattamenti)
        
        # Raggruppa prodotti per calcolare totali
        prodotti_totali = {}
        for trattamento in trattamenti:
            superficie_trattamento = trattamento.get_superficie_interessata()
            for tp in trattamento.trattamentoprodotto_set.all():
                # Usa il campo corretto (quantita_per_ettaro invece di quantita)
                quantita_per_ettaro = getattr(tp, 'quantita_per_ettaro', getattr(tp, 'quantita', 0))
                
                prodotto_nome = tp.prodotto.nome
                if prodotto_nome not in prodotti_totali:
                    prodotti_totali[prodotto_nome] = {
                        'nome': prodotto_nome,
                        'unita_misura': tp.prodotto.unita_misura,
                        'quantita_totale': Decimal('0')
                    }
                
                quantita_trattamento = Decimal(str(quantita_per_ettaro)) * Decimal(str(superficie_trattamento))
                prodotti_totali[prodotto_nome]['quantita_totale'] += quantita_trattamento
        
        # Context per il template
        context = {
            'cliente': cliente,
            'trattamenti': trattamenti,
            'superficie_totale': superficie_totale,
            'prodotti_totali': list(prodotti_totali.values()),
            'custom_notes': custom_notes,
            'data_comunicazione': timezone.now(),
            'numero_trattamenti': len(trattamenti)
        }
        
        print(f"🔍 DEBUG PDF: Context preparato con {len(context)} elementi")
        
        # Renderizza il template HTML
        try:
            html_content = render_to_string('pdf/comunicazione_trattamenti.html', context)
            print(f"🔍 DEBUG PDF: Template renderizzato, {len(html_content)} caratteri")
        except Exception as e:
            print(f"❌ DEBUG PDF: Errore template: {e}")
            raise Exception(f"Errore nel rendering del template: {str(e)}")
        
        # Genera PDF in base al motore disponibile
        if pdf_engine == 'weasyprint':
            # CSS per il PDF (inline per semplicità)
            css_content = """
                @page { size: A4; margin: 2cm; }
                body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.4; }
                .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #0d6efd; padding-bottom: 20px; }
                .company-info { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
                .treatment-item { border: 1px solid #dee2e6; margin-bottom: 15px; padding: 15px; page-break-inside: avoid; }
                table { width: 100%; border-collapse: collapse; }
                th, td { border: 1px solid #dee2e6; padding: 8px; text-align: left; }
                th { background: #f8f9fa; font-weight: bold; }
            """
            
            html_doc = HTML(string=html_content)
            pdf_content = html_doc.write_pdf(stylesheets=[CSS(string=css_content)])
            
        else:  # xhtml2pdf
            result = io.BytesIO()
            pdf = pisa.pisaDocument(io.BytesIO(html_content.encode('UTF-8')), result)
            
            if not pdf.err:
                pdf_content = result.getvalue()
            else:
                raise Exception("Errore nella generazione del PDF con xhtml2pdf")
        
        print(f"🔍 DEBUG PDF: PDF generato con successo, {len(pdf_content)} bytes")
        return pdf_content
        
    except Exception as e:
        print(f"❌ DEBUG PDF Generator: Errore: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Errore nella generazione del PDF: {str(e)}")


# Aggiungi anche la vista per il wizard:
def comunicazione_wizard(request):
    """Vista per il wizard di comunicazione trattamenti"""
    return render(request, 'comunicazione_wizard.html')

# Modifica la funzione api_bulk_action_trattamenti esistente per supportare le nuove modalità
@csrf_exempt
@require_http_methods(["POST"])
def api_bulk_action_trattamenti(request):
    """API per azioni in blocco sui trattamenti (versione aggiornata)"""
    try:
        import json
        from django.utils import timezone
        from django.db import transaction
        
        # Parse dei dati
        action = request.POST.get('action')
        communication_mode = request.POST.get('communication_mode', 'send_only')  # Nuova modalità
        trattamenti_ids_json = request.POST.get('trattamenti_ids', '[]')
        
        # Validazione azione
        valid_actions = ['comunica', 'completa', 'annulla']
        if action not in valid_actions:
            return JsonResponse({
                'success': False,
                'error': f'Azione non valida. Azioni disponibili: {", ".join(valid_actions)}'
            }, status=400)
        
        # Validazione modalità comunicazione
        valid_modes = ['send_only', 'download_only', 'send_and_download']
        if action == 'comunica' and communication_mode not in valid_modes:
            return JsonResponse({
                'success': False,
                'error': f'Modalità comunicazione non valida. Disponibili: {", ".join(valid_modes)}'
            }, status=400)
        
        # Parse degli ID
        try:
            trattamenti_ids = json.loads(trattamenti_ids_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Lista ID trattamenti non valida'
            }, status=400)
        
        if not trattamenti_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento selezionato'
            }, status=400)
        
        # Ottieni i trattamenti
        trattamenti = Trattamento.objects.filter(id__in=trattamenti_ids)
        
        if not trattamenti.exists():
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento trovato con gli ID specificati'
            }, status=404)
        
        # Contatori per i risultati
        successi = 0
        errori = []
        comunicazioni_inviate = 0
        pdf_downloads = []
        
        with transaction.atomic():
            for trattamento in trattamenti:
                try:
                    if action == 'comunica':
                        # Verifica che il trattamento sia programmato
                        if trattamento.stato != 'programmato':
                            errori.append(f'Trattamento #{trattamento.id}: non è in stato programmato (attuale: {trattamento.get_stato_display()})')
                            continue
                        
                        # Gestisci diverse modalità di comunicazione
                        email_sent = False
                        pdf_generated = False
                        
                        if communication_mode in ['send_only', 'send_and_download']:
                            # Invia email
                            try:
                                from .email_utils import send_trattamento_communication
                                risultato = send_trattamento_communication(trattamento.id)
                                
                                if risultato['success']:
                                    email_sent = True
                                    comunicazioni_inviate += 1
                                else:
                                    errori.append(f'Trattamento #{trattamento.id}: {risultato["error"]}')
                                    continue
                            except ImportError:
                                # Se email_utils non è disponibile, segna come inviato ma aggiungi warning
                                email_sent = True
                                errori.append(f'Trattamento #{trattamento.id}: comunicato ma email non inviata (modulo email non disponibile)')
                        
                        if communication_mode in ['download_only', 'send_and_download']:
                            # Genera PDF per download
                            try:
                                from .email_utils import generate_pdf_comunicazione
                                pdf_content = generate_pdf_comunicazione(trattamento.id)
                                
                                # Prepara info per download
                                filename = f"Trattamento_{trattamento.id}_{trattamento.cliente.nome.replace(' ', '_')}.pdf"
                                
                                # Crea URL temporaneo per download (implementazione semplificata)
                                download_url = f'/api/trattamenti/{trattamento.id}/download-pdf/'
                                
                                pdf_downloads.append({
                                    'trattamento_id': trattamento.id,
                                    'filename': filename,
                                    'url': download_url
                                })
                                
                                pdf_generated = True
                                
                            except Exception as e:
                                errori.append(f'Trattamento #{trattamento.id}: errore generazione PDF - {str(e)}')
                                continue
                        
                        # Aggiorna stato solo se almeno una operazione è riuscita
                        if email_sent or (communication_mode == 'download_only' and pdf_generated):
                            trattamento.stato = 'comunicato'
                            trattamento.data_comunicazione = timezone.now()
                            trattamento.save()
                            successi += 1
                    
                    elif action == 'completa':
                        # Verifica che il trattamento sia comunicato
                        if trattamento.stato != 'comunicato':
                            errori.append(f'Trattamento #{trattamento.id}: non è in stato comunicato (attuale: {trattamento.get_stato_display()})')
                            continue
                        
                        # Aggiorna a completato
                        trattamento.stato = 'completato'
                        trattamento.data_esecuzione_effettiva = timezone.now().date()
                        trattamento.save()
                        successi += 1
                    
                    elif action == 'annulla':
                        # Verifica che il trattamento non sia già completato
                        if trattamento.stato == 'completato':
                            errori.append(f'Trattamento #{trattamento.id}: non può essere annullato (già completato)')
                            continue
                        
                        # Aggiorna ad annullato
                        trattamento.stato = 'annullato'
                        trattamento.save()
                        successi += 1
                
                except Exception as e:
                    errori.append(f'Trattamento #{trattamento.id}: {str(e)}')
        
        # Prepara il messaggio di risposta
        if action == 'comunica':
            if communication_mode == 'send_only':
                message = f'{successi} trattament{("o" if successi == 1 else "i")} comunicat{("o" if successi == 1 else "i")} via email'
            elif communication_mode == 'download_only':
                message = f'{successi} trattament{("o" if successi == 1 else "i")} comunicat{("o" if successi == 1 else "i")} - PDF pronti per il download'
            else:  # send_and_download
                message = f'{successi} trattament{("o" if successi == 1 else "i")} comunicat{("o" if successi == 1 else "i")} via email + PDF scaricati'
            
            if comunicazioni_inviate > 0:
                message += f' ({comunicazioni_inviate} email inviate)'
                
        elif action == 'completa':
            message = f'{successi} trattament{("o" if successi == 1 else "i")} completat{("o" if successi == 1 else "i")} con successo'
        elif action == 'annulla':
            message = f'{successi} trattament{("o" if successi == 1 else "i")} annullat{("o" if successi == 1 else "i")} con successo'
        
        # Aggiungi errori al messaggio se presenti
        if errori:
            message += f'\n\nErrori ({len(errori)}):\n' + '\n'.join(errori[:5])  # Mostra max 5 errori
            if len(errori) > 5:
                message += f'\n... e altri {len(errori) - 5} errori'
        
        response_data = {
            'success': True,
            'message': message,
            'dettagli': {
                'azione': action,
                'modalita_comunicazione': communication_mode if action == 'comunica' else None,
                'totali_selezionati': len(trattamenti_ids),
                'successi': successi,
                'errori': len(errori),
                'comunicazioni_inviate': comunicazioni_inviate,
                'lista_errori': errori
            }
        }
        
        # Aggiungi info PDF se necessario
        if pdf_downloads:
            response_data['pdf_downloads'] = pdf_downloads
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante l\'elaborazione: {str(e)}'
        }, status=500)
                

@require_http_methods(["GET"])
def api_clienti_list(request):
    """API per ottenere lista clienti per i select"""
    try:
        clienti = Cliente.objects.all().order_by('nome')
        clienti_data = []
        for cliente in clienti:
            clienti_data.append({
                'id': cliente.id,
                'nome': cliente.nome
            })
        
        return JsonResponse({
            'success': True,
            'clienti': clienti_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def api_contoterzisti_list(request):
    """API per ottenere lista contoterzisti per i select"""
    try:
        contoterzisti = Contoterzista.objects.all().order_by('nome')
        contoterzisti_data = []
        for contoterzista in contoterzisti:
            contoterzisti_data.append({
                'id': contoterzista.id,
                'nome': contoterzista.nome,
                'email': contoterzista.email
            })
        
        return JsonResponse({
            'success': True,
            'contoterzisti': contoterzisti_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_contoterzista_create(request):
    """API per creare nuovo contoterzista (semplificata)"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        
        # Validazione
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome è obbligatorio'
            }, status=400)
            
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'L\'email è obbligatoria'
            }, status=400)
        
        # Validazione email
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'error': 'Indirizzo email non valido'
            }, status=400)
        
        # Verifica se esiste già un contoterzista con la stessa email
        if Contoterzista.objects.filter(email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un contoterzista con l\'email "{email}"'
            }, status=400)
        
        with transaction.atomic():
            contoterzista = Contoterzista.objects.create(
                nome=nome,
                email=email
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Contoterzista "{nome}" creato con successo',
                'contoterzista': {
                    'id': contoterzista.id,
                    'nome': contoterzista.nome,
                    'email': contoterzista.email
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore nella creazione: {str(e)}'
        }, status=500)



logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_weather_current(request):
    """Endpoint per ottenere i dati meteo correnti con gestione località"""
    try:
        # Ottieni parametri
        location = request.GET.get('location', None)
        force_refresh = request.GET.get('force_refresh', 'false').lower() == 'true'
        
        if location:
            location = location.strip()
            logger.info(f"🌍 Weather request for custom location: '{location}'")
        else:
            location = weather_service.default_location
            logger.info(f"🌍 Weather request for default location: '{location}'")
        
        # Se richiesto force refresh, cancella cache
        if force_refresh:
            logger.info(f"🔄 Force refresh requested for {location}")
            cache_key = weather_service.clear_location_cache(location)
        
        # Chiama il servizio meteo
        weather_data = weather_service.get_current_weather(location)
        
        # Genera consigli per trattamenti (se abilitati)
        advice = None
        try:
            advice = weather_service.get_treatment_advice(weather_data)
        except Exception as e:
            logger.warning(f"Treatment advice generation failed: {e}")
        
        # Prepara risposta
        response_data = {
            'success': True,
            'data': weather_data,
            'advice': advice,
            'location_requested': location,
            'location_found': weather_data.get('location', {}).get('name', 'Sconosciuta'),
            'from_cache': weather_data.get('from_cache', False),
            'cache_key': weather_data.get('cache_key', ''),
            'force_refresh': force_refresh
        }
        
        # Log dettagliato
        found_name = weather_data.get('location', {}).get('name', 'Unknown')
        cache_status = "cache" if weather_data.get('from_cache') else "API"
        logger.info(f"✅ Weather served: '{location}' -> '{found_name}' (from {cache_status})")
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        logger.error(f"Weather API configuration error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'configuration',
            'message': str(e),
            'location_requested': location
        }, status=400)
        
    except Exception as e:
        logger.error(f"Weather API unexpected error: {str(e)}")
        return JsonResponse({
            'success': False,  
            'error': 'api_error',
            'message': 'Errore nel recupero dei dati meteo',
            'location_requested': location
        }, status=500)

# Aggiungi endpoint per cancellare cache
@require_http_methods(["POST"])
def api_weather_clear_cache(request):
    """Cancella la cache per una località specifica"""
    try:
        import json
        data = json.loads(request.body)
        location = data.get('location', weather_service.default_location)
        
        cache_key = weather_service.clear_location_cache(location)
        
        return JsonResponse({
            'success': True,
            'message': f'Cache cleared for {location}',
            'cache_key': cache_key
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Endpoint di debug per vedere tutte le cache
@require_http_methods(["GET"])
def api_weather_debug_cache(request):
    """Debug: mostra tutte le località in cache"""
    try:
        cached_locations = weather_service.get_all_cached_locations()
        
        return JsonResponse({
            'success': True,
            'cached_locations': cached_locations,
            'default_location': weather_service.default_location,
            'cache_timeout': weather_service.cache_timeout
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    

@require_http_methods(["GET", "POST"])
def api_weather_location_test(request):
    """Endpoint per testare una località specifica"""
    try:
        if request.method == 'POST':
            import json
            data = json.loads(request.body)
            test_location = data.get('location', 'Turin')
        else:
            test_location = request.GET.get('location', 'Turin')
        
        logger.info(f"Testing weather for location: {test_location}")
        
        # Test con la località specificata
        weather_data = weather_service.get_current_weather(test_location)
        
        return JsonResponse({
            'success': True,
            'message': f'Test completato per {test_location}',
            'requested_location': test_location,
            'found_location': weather_data.get('location', {}).get('name'),
            'found_region': weather_data.get('location', {}).get('region'),
            'found_country': weather_data.get('location', {}).get('country'),
            'coordinates': {
                'lat': weather_data.get('location', {}).get('lat'),
                'lon': weather_data.get('location', {}).get('lon')
            },
            'weather': {
                'temp': weather_data.get('current', {}).get('temp_c'),
                'condition': weather_data.get('current', {}).get('condition', {}).get('text')
            }
        })
        
    except Exception as e:
        logger.error(f"Location test error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'Errore nel test per la località: {test_location}'
        })
    

@require_http_methods(["GET"])
def api_weather_debug_location(request, location):
    """Debug endpoint per testare come WeatherAPI interpreta le località"""
    try:
        logger.info(f"🔍 Debug richiesto per località: {location}")
        
        # Usa il metodo di debug del weather service
        debug_results = weather_service.debug_location_search(location)
        
        return JsonResponse({
            'success': True,
            'debug_location': location,
            'test_results': debug_results,
            'recommendation': get_location_recommendation(debug_results),
            'current_default': weather_service.default_location
        })
        
    except Exception as e:
        logger.error(f"Debug location error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'Errore nel debug per {location}'
        })

def get_location_recommendation(debug_results):
    """Suggerisce la migliore variante di località basata sui risultati"""
    
    successful_results = {k: v for k, v in debug_results.items() if v.get('success')}
    
    if not successful_results:
        return "Nessuna variante funzionante trovata"
    
    # Preferisci risultati che includono la regione corretta
    for location, result in successful_results.items():
        if 'Piemonte' in result.get('found_region', '') or 'Piedmont' in result.get('found_region', ''):
            return {
                'recommended': location,
                'reason': f"Trovata in regione corretta: {result['found_name']}, {result['found_region']}",
                'coordinates': result.get('coordinates')
            }
    
    # Altrimenti prendi il primo risultato
    first_result = list(successful_results.items())[0]
    return {
        'recommended': first_result[0],
        'reason': f"Prima opzione funzionante: {first_result[1]['found_name']}",
        'coordinates': first_result[1].get('coordinates')
    }


# domenico/views.py - Aggiungi queste views alla fine del file esistente

def aziende_cascine(request, cliente_id):
    """Vista cascine con ricerca e ordinamento case-insensitive"""

    from django.db.models import Sum, Count, Q
    from django.db.models.functions import Lower

    # Parametro di ricerca
    search_query = request.GET.get('search', '').strip()
    
    # Ottieni il cliente
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    # Carica cascine con terreni e contoterzista
    cascine = cliente.cascine.prefetch_related(
        'terreni', 'contoterzista'
    ).annotate(
        superficie_totale=Sum('terreni__superficie')
    )
    
    # Applica filtro di ricerca se presente
    if search_query:
        cascine = cascine.filter(
            nome__icontains=search_query
        )
    
    # Ordinamento case-insensitive
    cascine = cascine.order_by(Lower('nome'))
    
    # Prepara dati per il template
    cascine_data = []
    for cascina in cascine:
        cascina_dict = {
            'id': cascina.id,
            'nome': cascina.nome,
            'superficie_totale': cascina.superficie_totale or 0,
            'terreni_count': cascina.terreni.count(),
            'contoterzista': cascina.contoterzista,
            'terreni': list(cascina.terreni.all().order_by(Lower('nome')))
        }
        cascine_data.append(cascina_dict)
    
    context = {
        'cliente': cliente,
        'cascine_data': cascine_data,
        'search_query': search_query,
        'total_count': len(cascine_data),
        'breadcrumb_level': 'cascine'
    }
    
    return render(request, 'aziende_cascine.html', context)


def aziende_terreni(request, cascina_id):
    """Vista terreni con ricerca e ordinamento case-insensitive"""

    from django.db.models import Q
    from django.db.models.functions import Lower

    # Parametro di ricerca
    search_query = request.GET.get('search', '').strip()
    
    # Ottieni la cascina con cliente
    cascina = get_object_or_404(
        Cascina.objects.select_related('cliente', 'contoterzista'), 
        id=cascina_id
    )
    
    # Carica terreni
    terreni = cascina.terreni.all()
    
    # Applica filtro di ricerca se presente
    if search_query:
        terreni = terreni.filter(
            Q(nome__icontains=search_query) |
            Q(coltura__icontains=search_query)
        )
    
    # Ordinamento case-insensitive
    terreni = terreni.order_by(Lower('nome'))
    
    context = {
        'cascina': cascina,
        'cliente': cascina.cliente,
        'terreni': terreni,
        'search_query': search_query,
        'total_count': terreni.count(),
        'breadcrumb_level': 'terreni'
    }
    
    return render(request, 'aziende_terreni.html', context)


@require_http_methods(["POST"])
def edit_cliente(request, cliente_id):
    """Modifica nome cliente con logging"""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    old_name = cliente.nome  # Salva il nome precedente per il log
    
    nome = request.POST.get('nome', '').strip()
    if not nome:
        messages.error(request, 'Il nome del cliente è obbligatorio')
        return redirect('aziende')
    
    # Aggiorna il cliente
    cliente.nome = nome
    cliente.save()
    
    # Log dell'attività
    log_activity(
        activity_type='cliente_updated',
        title=f'Azienda modificata: {nome}',
        description=f'Il nome dell\'azienda è stato cambiato da "{old_name}" a "{nome}"',
        related_object=cliente,
        request=request,
        extra_data={
            'cliente_id': cliente.id,
            'old_name': old_name,
            'new_name': nome,
            'action': 'name_change'
        }
    )
    
    messages.success(request, f'Azienda "{nome}" modificata con successo!')
    
    # Mantieni la ricerca se presente
    search_param = request.GET.get('search', '')
    if search_param:
        return redirect(f'aziende?search={search_param}')
    
    return redirect('aziende')



@require_http_methods(["POST"])
def edit_cascina(request, cascina_id):
    """Modifica nome cascina con logging"""

    cascina = get_object_or_404(Cascina.objects.select_related('cliente'), id=cascina_id)
    old_name = cascina.nome  # Salva il nome precedente per il log
    
    nome = request.POST.get('nome', '').strip()
    if not nome:
        messages.error(request, 'Il nome della cascina è obbligatorio')
        return redirect('aziende_cascine', cliente_id=cascina.cliente.id)
    
    # Aggiorna la cascina
    cascina.nome = nome
    cascina.save()
    
    # Log dell'attività
    log_activity(
        activity_type='cascina_updated',
        title=f'Cascina modificata: {nome}',
        description=f'Il nome della cascina è stato cambiato da "{old_name}" a "{nome}" per l\'azienda {cascina.cliente.nome}',
        related_object=cascina,
        request=request,
        extra_data={
            'cascina_id': cascina.id,
            'cascina_old_name': old_name,
            'cascina_new_name': nome,
            'cliente_id': cascina.cliente.id,
            'cliente_nome': cascina.cliente.nome,
            'action': 'name_change'
        }
    )
    
    messages.success(request, f'Cascina "{nome}" modificata con successo!')
    
    # Mantieni la ricerca se presente
    search_param = request.GET.get('search', '')
    redirect_url = reverse('aziende_cascine', kwargs={'cliente_id': cascina.cliente.id})
    if search_param:
        redirect_url += f'?search={search_param}'
    
    return redirect(redirect_url)


@require_http_methods(["POST"])
def edit_terreno(request, terreno_id):
    """Modifica nome e superficie terreno con logging"""
    terreno = get_object_or_404(
        Terreno.objects.select_related('cascina__cliente'), 
        id=terreno_id
    )
    
    # Salva i valori precedenti per il log
    old_name = terreno.nome
    old_superficie = terreno.superficie
    
    nome = request.POST.get('nome', '').strip()
    superficie = request.POST.get('superficie', '').strip()
    
    if not nome:
        messages.error(request, 'Il nome del terreno è obbligatorio')
        return redirect('aziende_terreni', cascina_id=terreno.cascina.id)
    
    if not superficie:
        messages.error(request, 'La superficie è obbligatoria')
        return redirect('aziende_terreni', cascina_id=terreno.cascina.id)
    
    try:
        superficie_float = float(superficie)
        if superficie_float <= 0:
            raise ValueError("La superficie deve essere maggiore di 0")
    except ValueError:
        messages.error(request, 'La superficie deve essere un numero maggiore di 0')
        return redirect('aziende_terreni', cascina_id=terreno.cascina.id)
    
    # Aggiorna il terreno
    terreno.nome = nome
    terreno.superficie = superficie_float
    terreno.save()
    
    # Prepara i dettagli delle modifiche per il log
    changes = []
    if old_name != nome:
        changes.append(f'nome: "{old_name}" → "{nome}"')
    if float(old_superficie) != superficie_float:
        changes.append(f'superficie: {old_superficie} ha → {superficie_float} ha')
    
    changes_text = ', '.join(changes) if changes else 'nessuna modifica'
    
    # Log dell'attività
    log_activity(
        activity_type='terreno_updated',
        title=f'Terreno modificato: {nome}',
        description=f'Il terreno "{old_name}" della cascina {terreno.cascina.nome} è stato modificato: {changes_text}',
        related_object=terreno,
        request=request,
        extra_data={
            'terreno_id': terreno.id,
            'terreno_old_name': old_name,
            'terreno_new_name': nome,
            'old_superficie': float(old_superficie),
            'new_superficie': superficie_float,
            'cascina_id': terreno.cascina.id,
            'cascina_nome': terreno.cascina.nome,
            'cliente_id': terreno.cascina.cliente.id,
            'cliente_nome': terreno.cascina.cliente.nome,
            'changes': changes,
            'action': 'data_change'
        }
    )
    
    messages.success(request, f'Terreno "{nome}" modificato con successo!')
    
    # Mantieni la ricerca se presente
    search_param = request.GET.get('search', '')
    redirect_url = reverse('aziende_terreni', kwargs={'cascina_id': terreno.cascina.id})
    if search_param:
        redirect_url += f'?search={search_param}'
    

def comunicazione_wizard(request):
    """Vista per il wizard di comunicazione trattamenti"""
    return render(request, 'comunicazione_wizard.html')
    return redirect(redirect_url)

@require_http_methods(["GET"])
def api_search_aziende(request):
    """API per ricerca aziende in tempo reale"""

    from django.db.models import Sum, Count
    from django.db.models.functions import Lower

    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        # Cerca aziende
        aziende = Cliente.objects.filter(
            nome__icontains=query
        ).annotate(
            superficie_totale=Sum('cascine__terreni__superficie'),
            cascine_count=Count('cascine', distinct=True),
            terreni_count=Count('cascine__terreni', distinct=True)
        ).order_by(Lower('nome'))[:limit]
        
        results = []
        for azienda in aziende:
            results.append({
                'id': azienda.id,
                'nome': azienda.nome,
                'superficie_totale': float(azienda.superficie_totale or 0),
                'cascine_count': azienda.cascine_count,
                'terreni_count': azienda.terreni_count,
                'url': reverse('aziende_cascine', kwargs={'cliente_id': azienda.id})
            })
        
        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results)
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'results': []
        }, status=500)

@require_http_methods(["GET"])
def api_search_cascine(request, cliente_id):
    """API per ricerca cascine di un'azienda"""

    from django.db.models import Sum, Count, Q
    from django.db.models.functions import Lower

    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # Cerca cascine
        cascine = cliente.cascine.filter(
            nome__icontains=query
        ).annotate(
            superficie_totale=Sum('terreni__superficie'),
            terreni_count=Count('terreni', distinct=True)
        ).order_by(Lower('nome'))[:limit]
        
        results = []
        for cascina in cascine:
            results.append({
                'id': cascina.id,
                'nome': cascina.nome,
                'superficie_totale': float(cascina.superficie_totale or 0),
                'terreni_count': cascina.terreni_count,
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'url': reverse('aziende_terreni', kwargs={'cascina_id': cascina.id})
            })
        
        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results),
            'cliente': {
                'id': cliente.id,
                'nome': cliente.nome
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'results': []
        }, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def api_communication_status_check(request):
    """
    API per verificare lo stato dei trattamenti e aggiornare la vista
    dopo le comunicazioni progressive
    """
    try:
        data = json.loads(request.body)
        trattamenti_ids = data.get('trattamenti_ids', [])
        
        if not trattamenti_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento specificato'
            }, status=400)
        
        # Recupera i trattamenti con stato attuale
        trattamenti = Trattamento.objects.filter(
            id__in=trattamenti_ids
        ).select_related('cliente', 'cascina').prefetch_related('terreni')
        
        # Raggruppa per stato
        stati_trattamenti = {}
        trattamenti_comunicati = []
        trattamenti_rimanenti = []
        
        for trattamento in trattamenti:
            stato = trattamento.stato
            if stato not in stati_trattamenti:
                stati_trattamenti[stato] = 0
            stati_trattamenti[stato] += 1
            
            if stato == 'comunicato':
                trattamenti_comunicati.append(trattamento.id)
            elif stato == 'programmato':
                trattamenti_rimanenti.append({
                    'id': trattamento.id,
                    'cliente_nome': trattamento.cliente.nome,
                    'cascina_nome': trattamento.cascina.nome if trattamento.cascina else '',
                    'data_esecuzione': trattamento.data_esecuzione.strftime('%Y-%m-%d') if trattamento.data_esecuzione else None,
                    'superficie': float(trattamento.get_superficie_interessata())
                })
        
        return JsonResponse({
            'success': True,
            'data': {
                'stati_trattamenti': stati_trattamenti,
                'trattamenti_comunicati': trattamenti_comunicati,
                'trattamenti_rimanenti': trattamenti_rimanenti,
                'totale_originale': len(trattamenti_ids),
                'totale_comunicati': len(trattamenti_comunicati),
                'totale_rimanenti': len(trattamenti_rimanenti),
                'percentuale_completamento': round((len(trattamenti_comunicati) / len(trattamenti_ids)) * 100, 1) if trattamenti_ids else 0
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON non valido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la verifica stato: {str(e)}'
        }, status=500)
