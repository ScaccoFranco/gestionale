from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings 
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json
from .models import *

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



def home(request):
    """Vista home con statistiche"""
    from django.db.models import Sum, Count, Q
    
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
    }
    
    # Trattamenti recenti per l'attività
    trattamenti_recenti = Trattamento.objects.select_related(
        'cliente', 'cascina'
    ).prefetch_related('terreni')[:5]
    
    context = {
        'stats': stats,
        'trattamenti_recenti': trattamenti_recenti,
    }
    
    return render(request, 'home.html', context)

def aziende(request):
    """Vista aziende con struttura ad albero"""
    from django.db.models import Sum, Count, Q
    
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
    ).order_by('nome')
    
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
        
        for cascina in cliente.cascine.all():
            superficie_cascina = sum(terreno.superficie for terreno in cascina.terreni.all())
            
            cascina_data = {
                'id': cascina.id,
                'nome': cascina.nome,
                'superficie_totale': superficie_cascina,
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'terreni': list(cascina.terreni.all())
            }
            
            cliente_data['cascine'].append(cascina_data)
        
        aziende_tree.append(cliente_data)
    
    context = {
        'aziende_tree': aziende_tree,
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
            Q(note__icontains=filters['search']) |
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
        'stats': stats,
        'filters': filters,
        'clienti': clienti,
        'cascine': cascine,
        'contoterzisti': contoterzisti,
        'view_type': view_type,
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

@csrf_exempt
@require_http_methods(["POST"])
def api_send_comunicazione(request, trattamento_id):
    """API per inviare la comunicazione email di un trattamento"""
    try:
        force_send = request.POST.get('force_send', 'false').lower() == 'true'
        
        # Invia la comunicazione
        risultato = send_trattamento_communication(trattamento_id, force_send=force_send)
        
        if risultato['success']:
            return JsonResponse({
                'success': True,
                'message': f'Comunicazione inviata con successo a {risultato["destinatari_count"]} destinatari',
                'destinatari': risultato['destinatari'],
                'comunicazione_id': risultato['comunicazione_id']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': risultato['error']
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'aggiunta del contatto: {str(e)}'
        }, status=500)
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

@csrf_exempt
@require_http_methods(["POST"])
def api_create_trattamento(request):
    """API per creare un nuovo trattamento con quantità per ettaro - versione debug"""
    try:
        # DEBUG: Log di tutti i dati ricevuti
        print("=== DEBUG API CREATE TRATTAMENTO ===")
        print("POST data:", dict(request.POST))
        print("FILES:", dict(request.FILES))
        print("Content-Type:", request.content_type)
        
        with transaction.atomic():
            # Parsing dei dati
            cliente_id = request.POST.get('cliente')
            cascina_id = request.POST.get('cascina') or None
            livello_applicazione = request.POST.get('livello_applicazione', 'cliente')
            data_esecuzione_prevista = request.POST.get('data_esecuzione_prevista') or None
            note = request.POST.get('note', '')
            
            print(f"Dati parsati:")
            print(f"  - cliente_id: {cliente_id}")
            print(f"  - cascina_id: {cascina_id}")
            print(f"  - livello_applicazione: {livello_applicazione}")
            print(f"  - data_esecuzione_prevista: {data_esecuzione_prevista}")
            print(f"  - note: {note}")
            
            # Validazione cliente
            if not cliente_id:
                print("ERRORE: Cliente mancante")
                return JsonResponse({
                    'success': False, 
                    'error': 'Cliente è obbligatorio'
                }, status=400)
            
            # Parsing dei prodotti con quantità per ettaro
            prodotti_data_raw = request.POST.get('prodotti_data', '[]')
            print(f"Prodotti data raw: {prodotti_data_raw}")
            
            try:
                prodotti_data = json.loads(prodotti_data_raw)
                print(f"Prodotti data parsed: {prodotti_data}")
            except json.JSONDecodeError as e:
                print(f"ERRORE JSON: {e}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Dati prodotti non validi: {str(e)}'
                }, status=400)
            
            if not prodotti_data:
                print("ERRORE: Nessun prodotto")
                return JsonResponse({
                    'success': False, 
                    'error': 'È necessario specificare almeno un prodotto'
                }, status=400)
            
            # Validazione dei prodotti
            for i, prodotto_data in enumerate(prodotti_data):
                print(f"Validazione prodotto {i+1}: {prodotto_data}")
                
                if 'quantita_per_ettaro' not in prodotto_data:
                    print(f"ERRORE: quantita_per_ettaro mancante in prodotto {i+1}")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Prodotto {i+1}: quantita_per_ettaro mancante'
                    }, status=400)
                
                if 'prodotto_id' not in prodotto_data:
                    print(f"ERRORE: prodotto_id mancante in prodotto {i+1}")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Prodotto {i+1}: prodotto_id mancante'
                    }, status=400)
                
                try:
                    float(prodotto_data['quantita_per_ettaro'])
                    print(f"  ✓ Quantità valida: {prodotto_data['quantita_per_ettaro']}")
                except ValueError:
                    print(f"ERRORE: quantità non numerica in prodotto {i+1}")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Prodotto {i+1}: quantità per ettaro deve essere un numero'
                    }, status=400)
            
            # Verifica che il cliente esista
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                print(f"Cliente trovato: {cliente.nome}")
            except Cliente.DoesNotExist:
                print(f"ERRORE: Cliente {cliente_id} non trovato")
                return JsonResponse({
                    'success': False, 
                    'error': 'Cliente non trovato'
                }, status=404)
            
            # Verifica cascina se specificata
            if cascina_id:
                try:
                    cascina = Cascina.objects.get(id=cascina_id, cliente=cliente)
                    print(f"Cascina trovata: {cascina.nome}")
                except Cascina.DoesNotExist:
                    print(f"ERRORE: Cascina {cascina_id} non trovata per cliente {cliente_id}")
                    return JsonResponse({
                        'success': False, 
                        'error': 'Cascina non trovata per questo cliente'
                    }, status=404)
            
            # Creazione del trattamento
            print("Creazione trattamento...")
            trattamento = Trattamento.objects.create(
                cliente_id=cliente_id,
                cascina_id=cascina_id,
                livello_applicazione=livello_applicazione,
                data_esecuzione_prevista=data_esecuzione_prevista,
                note=note,
                stato='programmato'
            )
            print(f"Trattamento creato con ID: {trattamento.id}")
            
            # Aggiungi terreni se specificati
            terreni_selezionati = request.POST.getlist('terreni_selezionati')
            print(f"Terreni selezionati: {terreni_selezionati}")
            
            if terreni_selezionati:
                terreni_validi = Terreno.objects.filter(id__in=terreni_selezionati)
                
                if cascina_id:
                    terreni_validi = terreni_validi.filter(cascina_id=cascina_id)
                
                if terreni_validi.count() != len(terreni_selezionati):
                    print(f"ERRORE: Terreni non validi. Richiesti: {len(terreni_selezionati)}, Trovati: {terreni_validi.count()}")
                    return JsonResponse({
                        'success': False, 
                        'error': 'Alcuni terreni selezionati non sono validi'
                    }, status=400)
                
                trattamento.terreni.set(terreni_validi)
                print(f"Terreni assegnati: {[t.nome for t in terreni_validi]}")
            
            # Aggiungi prodotti
            prodotti_creati = []
            for i, prodotto_data in enumerate(prodotti_data):
                try:
                    print(f"Creazione prodotto {i+1}: {prodotto_data}")
                    
                    # Verifica che il prodotto esista
                    prodotto = Prodotto.objects.get(id=prodotto_data['prodotto_id'])
                    print(f"  ✓ Prodotto trovato: {prodotto.nome}")
                    
                    trattamento_prodotto = TrattamentoProdotto.objects.create(
                        trattamento=trattamento,
                        prodotto=prodotto,
                        quantita_per_ettaro=prodotto_data['quantita_per_ettaro']
                    )
                    print(f"  ✓ TrattamentoProdotto creato: {trattamento_prodotto}")
                    
                    prodotti_creati.append({
                        'prodotto_nome': prodotto.nome,
                        'quantita_per_ettaro': float(trattamento_prodotto.quantita_per_ettaro),
                        'quantita_totale': float(trattamento_prodotto.quantita_totale),
                        'unita_misura': prodotto.unita_misura
                    })
                    
                except Prodotto.DoesNotExist:
                    print(f"ERRORE: Prodotto {prodotto_data['prodotto_id']} non trovato")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Prodotto con ID {prodotto_data["prodotto_id"]} non trovato'
                    }, status=404)
                except KeyError as e:
                    print(f"ERRORE: Campo mancante in prodotto {i+1}: {e}")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Prodotto {i+1}: campo mancante {str(e)}'
                    }, status=400)
                except Exception as e:
                    print(f"ERRORE: Errore generico prodotto {i+1}: {e}")
                    return JsonResponse({
                        'success': False, 
                        'error': f'Errore nell\'aggiunta del prodotto {i+1}: {str(e)}'
                    }, status=400)
            
            # Calcola informazioni aggiuntive
            superficie_interessata = trattamento.get_superficie_interessata()
            contoterzista = trattamento.get_contoterzista()
            
            print(f"✅ Trattamento creato con successo!")
            print(f"  - ID: {trattamento.id}")
            print(f"  - Superficie: {superficie_interessata} ha")
            print(f"  - Prodotti: {len(prodotti_creati)}")
            print(f"  - Contoterzista: {contoterzista.nome if contoterzista else 'Nessuno'}")
            
            return JsonResponse({
                'success': True, 
                'trattamento_id': trattamento.id,
                'message': 'Trattamento creato con successo',
                'dettagli': {
                    'livello_applicazione': trattamento.livello_applicazione,
                    'superficie_interessata': float(superficie_interessata),
                    'contoterzista': contoterzista.nome if contoterzista else None,
                    'prodotti_count': len(prodotti_creati),
                    'terreni_count': trattamento.terreni.count() if livello_applicazione == 'terreno' else 0,
                    'prodotti_dettagli': prodotti_creati
                }
            })
            
    except Exception as e:
        print(f"💥 ERRORE GENERALE: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Errore durante la creazione: {str(e)}'
        }, status=500)
    
    
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
            'data_esecuzione_prevista': trattamento.data_esecuzione_prevista.isoformat() if trattamento.data_esecuzione_prevista else None,
            'data_esecuzione_effettiva': trattamento.data_esecuzione_effettiva.isoformat() if trattamento.data_esecuzione_effettiva else None,
            'note': trattamento.note,
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

@csrf_exempt
@require_http_methods(["POST"])
def api_add_contatto_cliente(request, cliente_id):
    """API per aggiungere un contatto email a un cliente"""
    try:
        # Verifica che il cliente esista
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # Ottieni i dati dal form
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
        
        # Verifica che non esista già un contatto con la stessa email per questo cliente
        if ContattoEmail.objects.filter(cliente=cliente, email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un contatto con l\'email "{email}" per questo cliente'
            }, status=400)

        # Crea il contatto
        contatto = ContattoEmail.objects.create(
            cliente=cliente,
            nome=nome,
            email=email
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Contatto {nome} aggiunto con successo',
            'contatto': {
                'id': contatto.id,
                'nome': contatto.nome,
                'email': contatto.email,
                'cliente_nome': cliente.nome
            }
        })
        
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente non trovato'
        }, status=404)
    except Exception as e:
        print(f"Errore in api_add_contatto_cliente: {str(e)}")
        print(f"POST data: {dict(request.POST)}")
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'aggiunta del contatto: {str(e)}'
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
 

@csrf_exempt
@require_http_methods(["POST"])
def api_communication_preview(request):
    """API per generare anteprima delle comunicazioni email"""
    try:
        import json
        
        # Parse degli ID trattamenti
        trattamenti_ids_json = request.POST.get('trattamenti_ids', '[]')
        
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
        trattamenti = Trattamento.objects.filter(
            id__in=trattamenti_ids,
            stato='programmato'  # Solo trattamenti programmati
        ).select_related('cliente').prefetch_related('cliente__contatti_email')
        
        if not trattamenti.exists():
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento programmato trovato con gli ID specificati'
            }, status=404)
        
        # Genera anteprime per ogni trattamento
        email_previews = []
        all_recipients = []
        
        for trattamento in trattamenti:

            # Prepara dati email per questo trattamento
            recipients = []
            for contatto in trattamento.cliente.contatti_email:
                recipients.append(contatto.email)
                all_recipients.append({
                    'nome': contatto.nome,
                    'email': contatto.email,
                    'trattamento_id': trattamento.id,
                    'cliente_nome': trattamento.cliente.nome
                })
            
            # Genera anteprima email
            oggetto = f"Trattamento #{trattamento.id} - {trattamento.cliente.nome}"
            if trattamento.data_esecuzione_prevista:
                oggetto += f" - Esecuzione prevista: {trattamento.data_esecuzione_prevista.strftime('%d/%m/%Y')}"
            
            # Genera corpo email (usa funzione esistente se disponibile)
            try:
                from .email_utils import generate_email_body
                corpo_email = generate_email_body(trattamento)
            except (ImportError, AttributeError):
                # Fallback se email_utils non disponibile
                corpo_email = f"""
Gentile Contoterzista,

in allegato la comunicazione per il trattamento #{trattamento.id}.

DETTAGLI TRATTAMENTO:
• Cliente: {trattamento.cliente.nome}
• Superficie interessata: {trattamento.get_superficie_interessata():.2f} ettari
• Stato: {trattamento.get_stato_display()}
"""
                if trattamento.data_esecuzione_prevista:
                    corpo_email += f"• Data esecuzione prevista: {trattamento.data_esecuzione_prevista.strftime('%d/%m/%Y')}\n"
                
                corpo_email += f"• Prodotti: {trattamento.trattamentoprodotto_set.count()} prodotti specificati\n\n"
                
                if trattamento.note:
                    corpo_email += f"NOTE SPECIALI:\n{trattamento.note}\n\n"
                
                corpo_email += """
Si prega di confermare la ricezione e di comunicare l'avvenuta esecuzione del trattamento.

Cordiali saluti,
Domenico Franco
Sistema di Gestione Trattamenti Agricoli
"""
            
            # Nome file PDF
            filename = f"Trattamento_{trattamento.id}_{trattamento.cliente.nome.replace(' ', '_')}.pdf"
            
            email_previews.append({
                'trattamento_id': trattamento.id,
                'cliente_nome': trattamento.cliente.nome,
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@gestionale.com'),
                'recipients': recipients,
                'subject': oggetto,
                'body': corpo_email,
                'attachments': [filename]
            })
        
        if not email_previews:
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento ha contatti email attivi configurati'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'trattamenti_count': len(email_previews),
            'total_recipients': len(set(r['email'] for r in all_recipients)),
            'email_previews': email_previews,
            'all_recipients': all_recipients
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la generazione anteprima: {str(e)}'
        }, status=500)

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

@csrf_exempt
@require_http_methods(["POST"])
def api_cliente_create(request):
    """API per creare nuovo cliente (semplificata)"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        nome = data.get('nome', '').strip()
        
        # Validazione
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome del cliente è obbligatorio'
            }, status=400)
            
        # Verifica se esiste già
        if Cliente.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un cliente con il nome "{nome}"'
            }, status=400)
        
        with transaction.atomic():
            # Crea cliente
            cliente = Cliente.objects.create(nome=nome)
            
            # Gestisci contatti se presenti
            contatti = data.get('contatti', [])
            contatti_creati = []
            
            for contatto_data in contatti:
                if contatto_data.get('nome') and contatto_data.get('email'):
                    contatto = ContattoEmail.objects.create(
                        cliente=cliente,
                        nome=contatto_data['nome'],
                        email=contatto_data['email'],
                    )
                    contatti_creati.append(contatto.nome)
            
            return JsonResponse({
                'success': True,
                'message': f'Cliente "{nome}" creato con successo',
                'cliente': {
                    'id': cliente.id,
                    'nome': cliente.nome
                },
                'contatti_creati': len(contatti_creati)
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
def api_cascina_create(request):
    """API per creare nuova cascina (semplificata)"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        cliente_id = data.get('cliente_id')
        nome = data.get('nome', '').strip()
        contoterzista_id = data.get('contoterzista_id') or None
        
        # Validazione
        if not cliente_id:
            return JsonResponse({
                'success': False,
                'error': 'Il cliente è obbligatorio'
            }, status=400)
            
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome della cascina è obbligatorio'
            }, status=400)
        
        # Verifica che il cliente esista
        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cliente non trovato'
            }, status=404)
        
        # Verifica che il contoterzista esista (se specificato)
        contoterzista = None
        if contoterzista_id:
            try:
                contoterzista = Contoterzista.objects.get(id=contoterzista_id)
            except Contoterzista.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Contoterzista non trovato'
                }, status=404)
        
        # Verifica unicità nome per cliente
        if Cascina.objects.filter(cliente=cliente, nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Il cliente "{cliente.nome}" ha già una cascina chiamata "{nome}"'
            }, status=400)
        
        with transaction.atomic():
            cascina = Cascina.objects.create(
                cliente=cliente,
                nome=nome,
                contoterzista=contoterzista
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Cascina "{nome}" creata con successo',
                'cascina': {
                    'id': cascina.id,
                    'nome': cascina.nome,
                    'cliente': cascina.cliente.nome,
                    'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None
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