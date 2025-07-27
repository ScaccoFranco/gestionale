from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
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
    """Dashboard trattamenti con statistiche"""
    from django.db.models import Count
    
    # Calcola statistiche
    stats = {
        'totali': Trattamento.objects.count(),
        'programmati': Trattamento.objects.filter(stato='programmato').count(),
        'comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'in_esecuzione': Trattamento.objects.filter(stato='in_esecuzione').count(),
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
    """Vista tabella trattamenti con filtri"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Query base
    trattamenti = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni', 'trattamentoprodotto_set__prodotto')
    
    # Mappatura corretta degli stati
    stati_mapping = {
        'programmati': 'programmato',
        'comunicati': 'comunicato', 
        'in_esecuzione': 'in_esecuzione',
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
        # Se il tipo non è riconosciuto, non filtrare
        print(f"Tipo vista non riconosciuto: {view_type}")
    
    # Resto del codice rimane uguale...
    
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
    
    # Debug: stampa il numero finale di trattamenti
    print(f"Trattamenti finali dopo tutti i filtri: {trattamenti.count()}")
    
    # Paginazione
    paginator = Paginator(trattamenti, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche per la vista
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
    
    # Titoli e descrizioni per vista
    view_info = {
        'tutti': {
            'title': 'Tutti i Trattamenti',
            'description': 'Elenco completo di tutti i trattamenti registrati nel sistema'
        },
        'programmati': {
            'title': 'Trattamenti Programmati',
            'description': 'Trattamenti pianificati che necessitano di essere comunicati'
        },
        'comunicati': {
            'title': 'Trattamenti Comunicati',
            'description': 'Trattamenti comunicati ai contoterzisti e in attesa di esecuzione'
        },
        'in_esecuzione': {
            'title': 'Trattamenti In Esecuzione',
            'description': 'Trattamenti attualmente in corso di esecuzione'
        },
        'completati': {
            'title': 'Trattamenti Completati',
            'description': 'Trattamenti eseguiti con successo'
        },
        'annullati': {
            'title': 'Trattamenti Annullati',
            'description': 'Trattamenti cancellati o non eseguiti'
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
    
    # Carica tutti i clienti con i loro contatti
    clienti = Cliente.objects.prefetch_related('contatti_email').order_by('nome')
    
    # Statistiche
    stats = {
        'clienti_totali': Cliente.objects.count(),
        'clienti_con_contatti': Cliente.objects.filter(contatti_email__isnull=False).distinct().count(),
        'contatti_totali': ContattoEmail.objects.count(),
        'contatti_attivi': ContattoEmail.objects.filter(attivo=True).count(),
    }
    
    context = {
        'clienti': clienti,
        'stats': stats,
    }
    
    return render(request, 'gestione_contatti_email.html', context)

def comunicazioni_dashboard(request):
    """Dashboard per visualizzare tutte le comunicazioni inviate"""
    
    # Filtri
    cliente_filter = request.GET.get('cliente', '')
    data_da = request.GET.get('data_da', '')
    data_a = request.GET.get('data_a', '')
    solo_errori = request.GET.get('solo_errori', '') == 'on'
    
    # Query base
    comunicazioni = ComunicazioneTrattamento.objects.select_related(
        'trattamento__cliente'
    ).order_by('-data_invio')
    
    # Applica filtri
    if cliente_filter:
        comunicazioni = comunicazioni.filter(trattamento__cliente_id=cliente_filter)
    
    if data_da:
        comunicazioni = comunicazioni.filter(data_invio__date__gte=data_da)
    
    if data_a:
        comunicazioni = comunicazioni.filter(data_invio__date__lte=data_a)
    
    if solo_errori:
        comunicazioni = comunicazioni.filter(inviato_con_successo=False)
    
    # Paginazione
    paginator = Paginator(comunicazioni, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche
    stats = get_comunicazioni_stats()
    
    # Per i dropdown dei filtri
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

@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def api_manage_contatto(request, contatto_id):
    """API per modificare o eliminare un contatto email"""
    try:
        if request.method == 'POST':
            # Modifica contatto
            contatto = get_object_or_404(ContattoEmail, id=contatto_id)
            
            kwargs = {}
            if 'nome' in request.POST:
                kwargs['nome'] = request.POST.get('nome').strip()
            if 'email' in request.POST:
                kwargs['email'] = request.POST.get('email').strip()
            if 'ruolo' in request.POST:
                kwargs['ruolo'] = request.POST.get('ruolo').strip()
            if 'telefono' in request.POST:
                kwargs['telefono'] = request.POST.get('telefono').strip()
            if 'priorita' in request.POST:
                kwargs['priorita'] = int(request.POST.get('priorita'))
            if 'attivo' in request.POST:
                kwargs['attivo'] = request.POST.get('attivo', 'false').lower() == 'true'
            if 'note' in request.POST:
                kwargs['note'] = request.POST.get('note').strip()
            
            risultato = update_contatto_email(contatto_id, **kwargs)
            
            if risultato['success']:
                # Ricarica il contatto aggiornato
                contatto.refresh_from_db()
                return JsonResponse({
                    'success': True,
                    'message': risultato['message'],
                    'contatto': {
                        'id': contatto.id,
                        'nome': contatto.nome,
                        'email': contatto.email,
                        'ruolo': contatto.ruolo,
                        'telefono': contatto.telefono,
                        'priorita': contatto.priorita,
                        'attivo': contatto.attivo,
                        'note': contatto.note
                    }
                })
            else:
                return JsonResponse(risultato, status=400)
            
        elif request.method == 'DELETE':
            # Elimina contatto
            risultato = delete_contatto_email(contatto_id)
            
            if risultato['success']:
                return JsonResponse(risultato)
            else:
                return JsonResponse(risultato, status=400)
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Priorità deve essere un numero'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
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
                'ruolo': contatto.ruolo,
                'telefono': contatto.telefono,
                'priorita': contatto.priorita,
                'attivo': contatto.attivo,
                'note': contatto.note
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
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        ruolo = request.POST.get('ruolo', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        priorita = int(request.POST.get('priorita', 1))
        note = request.POST.get('note', '').strip()
        
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
        
        # Aggiungi il contatto
        risultato = add_contatto_email(
            cliente_id=cliente_id,
            nome=nome,
            email=email,
            ruolo=ruolo,
            telefono=telefono,
            priorita=priorita,
            note=note
        )
        
        if risultato['success']:
            return JsonResponse(risultato)
        else:
            return JsonResponse(risultato, status=400)
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Priorità deve essere un numero'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'invio della comunicazione: {str(e)}'
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
                    'telefono': cascina.contoterzista.telefono,
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