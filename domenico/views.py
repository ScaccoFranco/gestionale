from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
import json
from .models import *

def home(request):
    """Vista per la homepage con statistiche generali"""
    
    # Statistiche per la dashboard
    stats = {
        'clienti_totali': Cliente.objects.count(),
        'cascine_totali': Cascina.objects.count(),
        'terreni_totali': Terreno.objects.count(),
        'superficie_totale': Terreno.objects.aggregate(
            totale=Sum('superficie')
        )['totale'] or 0,
        'trattamenti_programmati': Trattamento.objects.filter(
            stato='programmato'
        ).count(),
        'trattamenti_comunicati': Trattamento.objects.filter(
            stato='comunicato'
        ).count(),
        'trattamenti_oggi': Trattamento.objects.filter(
            data_esecuzione_prevista=timezone.now().date()
        ).count(),
        'trattamenti_totali': Trattamento.objects.count(),
    }
    
    # Trattamenti recenti (ultimi 5) - corretto senza contoterzista
    trattamenti_recenti = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni', 'prodotti').order_by('-data_inserimento')[:5]
    
    context = {
        'stats': stats,
        'trattamenti_recenti': trattamenti_recenti,
    }
    
    return render(request, 'home.html', context)

def aziende(request):
    """Vista per la pagina delle aziende con struttura a rettangoli"""
    
    # Carica tutti i clienti con le relative cascine e terreni
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
    
    # Struttura dati per l'interfaccia a rettangoli
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
            # Calcola i trattamenti per questa specifica cascina
            cascina_trattamenti_prog = cascina.get_trattamenti_attivi().filter(stato='programmato').count()
            cascina_trattamenti_com = cascina.get_trattamenti_attivi().filter(stato='comunicato').count()
            
            # Calcola la superficie totale della cascina
            superficie_cascina = sum(terreno.superficie for terreno in cascina.terreni.all())
            
            cascina_data = {
                'id': cascina.id,
                'nome': cascina.nome,
                'superficie_totale': superficie_cascina,
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'contoterzista_id': cascina.contoterzista.id if cascina.contoterzista else None,
                'trattamenti_programmati': cascina_trattamenti_prog,
                'trattamenti_comunicati': cascina_trattamenti_com,
                'terreni': list(cascina.terreni.all())
            }
            
            cliente_data['cascine'].append(cascina_data)
        
        aziende_tree.append(cliente_data)
    
    context = {
        'aziende_tree': aziende_tree,
    }
    
    return render(request, 'aziende.html', context)

def trattamenti(request):
    """Vista per la gestione completa dei trattamenti"""
    
    # Parametro view per determinare quale vista mostrare
    view_type = request.GET.get('view', 'dashboard')
    
    if view_type == 'dashboard':
        # Vista dashboard principale con statistiche e cronologia
        return trattamenti_dashboard(request)
    else:
        # Vista dettagliata con tabella filtrata
        return trattamenti_detail_view(request, view_type)

def trattamenti_dashboard(request):
    """Dashboard principale dei trattamenti"""
    
    # Statistiche generali
    stats = {
        'totali': Trattamento.objects.count(),
        'programmati': Trattamento.objects.filter(stato='programmato').count(),
        'comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'in_esecuzione': Trattamento.objects.filter(stato='in_esecuzione').count(),
        'completati': Trattamento.objects.filter(stato='completato').count(),
        'annullati': Trattamento.objects.filter(stato='annullato').count(),
    }
    
    # Trattamenti recenti (ultimi 10)
    trattamenti_recenti = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni', 'prodotti').order_by('-data_inserimento')[:10]
    
    context = {
        'stats': stats,
        'trattamenti_recenti': trattamenti_recenti,
        'view_type': 'dashboard',
    }
    
    return render(request, 'trattamenti.html', context)

def trattamenti_detail_view(request, view_type):
    """Vista dettagliata con tabella filtrata"""
    
    # Filtri dalla query string
    cliente_filter = request.GET.get('cliente', '')
    cascina_filter = request.GET.get('cascina', '')
    contoterzista_filter = request.GET.get('contoterzista', '')
    search_filter = request.GET.get('search', '')
    
    # Query base
    trattamenti_list = Trattamento.objects.select_related(
        'cliente', 'cascina', 'cascina__contoterzista'
    ).prefetch_related('terreni', 'prodotti', 'trattamentoprodotto_set__prodotto')
    
    # Applica filtro per stato
    stato_map = {
        'tutti': None,
        'programmati': 'programmato',
        'comunicati': 'comunicato',
        'in_esecuzione': 'in_esecuzione',
        'completati': 'completato',
        'annullati': 'annullato',
    }
    
    if view_type in stato_map and stato_map[view_type]:
        trattamenti_list = trattamenti_list.filter(stato=stato_map[view_type])
    
    # Altri filtri
    if cliente_filter:
        trattamenti_list = trattamenti_list.filter(cliente_id=cliente_filter)
    if cascina_filter:
        trattamenti_list = trattamenti_list.filter(cascina_id=cascina_filter)
    if contoterzista_filter:
        trattamenti_list = trattamenti_list.filter(cascina__contoterzista_id=contoterzista_filter)
    if search_filter:
        trattamenti_list = trattamenti_list.filter(
            Q(cliente__nome__icontains=search_filter) |
            Q(cascina__nome__icontains=search_filter) |
            Q(note__icontains=search_filter)
        )
    
    # Ordina per data inserimento (più recenti prima)
    trattamenti_list = trattamenti_list.order_by('-data_inserimento')
    
    # Statistiche per questa vista
    stats = {
        'totali': Trattamento.objects.count(),
        'programmati': Trattamento.objects.filter(stato='programmato').count(),
        'comunicati': Trattamento.objects.filter(stato='comunicato').count(),
        'in_esecuzione': Trattamento.objects.filter(stato='in_esecuzione').count(),
        'completati': Trattamento.objects.filter(stato='completato').count(),
        'annullati': Trattamento.objects.filter(stato='annullato').count(),
        'filtrati': trattamenti_list.count(),
    }
    
    # Per i dropdown dei filtri
    clienti = Cliente.objects.all().order_by('nome')
    cascine = Cascina.objects.select_related('contoterzista', 'cliente').all().order_by('nome')
    contoterzisti = Contoterzista.objects.all().order_by('nome')
    
    # Paginazione
    from django.core.paginator import Paginator
    paginator = Paginator(trattamenti_list, 20)  # 20 trattamenti per pagina
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'trattamenti': page_obj,
        'stats': stats,
        'view_type': view_type,
        'view_title': get_view_title(view_type),
        'view_description': get_view_description(view_type),
        'clienti': clienti,
        'cascine': cascine,
        'contoterzisti': contoterzisti,
        'filters': {
            'cliente': cliente_filter,
            'cascina': cascina_filter,
            'contoterzista': contoterzista_filter,
            'search': search_filter,
        },
        'stati_choices': Trattamento.STATI_CHOICES,
    }
    
    return render(request, 'trattamenti_table.html', context)

def get_view_title(view_type):
    """Restituisce il titolo per il tipo di vista"""
    titles = {
        'tutti': 'Tutti i Trattamenti',
        'programmati': 'Trattamenti Programmati',
        'comunicati': 'Trattamenti Comunicati',
        'in_esecuzione': 'Trattamenti in Esecuzione',
        'completati': 'Trattamenti Completati',
        'annullati': 'Trattamenti Annullati',
    }
    return titles.get(view_type, 'Trattamenti')

def get_view_description(view_type):
    """Restituisce la descrizione per il tipo di vista"""
    descriptions = {
        'tutti': 'Elenco completo di tutti i trattamenti con filtri avanzati',
        'programmati': 'Trattamenti pianificati che necessitano di essere comunicati',
        'comunicati': 'Trattamenti comunicati ai contoterzisti in attesa di esecuzione',
        'in_esecuzione': 'Trattamenti attualmente in corso di esecuzione',
        'completati': 'Trattamenti eseguiti e completati con successo',
        'annullati': 'Trattamenti cancellati o annullati',
    }
    return descriptions.get(view_type, 'Gestione trattamenti')

# Aggiungi anche questa funzione helper per i template:
def get_livello_applicazione_display_for_template():
    """Funzione helper per mostrare il livello di applicazione nei template"""
    # Questa può essere usata come template filter se necessario
    pass




def inserisci(request):
    """Vista per la pagina di inserimento (può contenere vari form o aprire modal)"""
    
    # Dati necessari per i form/modal
    clienti = Cliente.objects.all().order_by('nome')
    cascine = Cascina.objects.select_related('contoterzista').all().order_by('nome')
    prodotti = Prodotto.objects.all().order_by('nome')
    
    context = {
        'clienti': clienti,
        'cascine': cascine,
        'prodotti': prodotti,
    }
    
    return render(request, 'inserisci.html', context)

def database(request):
    """Vista per la gestione del database"""
    
    stats = {
        'clienti': Cliente.objects.count(),
        'cascine': Cascina.objects.count(),
        'terreni': Terreno.objects.count(),
        'contoterzisti': Contoterzista.objects.count(),
        'prodotti': Prodotto.objects.count(),
        'principi_attivi': PrincipioAttivo.objects.count(),
        'trattamenti': Trattamento.objects.count(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'database.html', context)

# ============ API ENDPOINTS ============

def api_cascine_by_cliente(request, cliente_id):
    """API per ottenere le cascine di un cliente"""
    try:
        cascine = Cascina.objects.filter(cliente_id=cliente_id).select_related('contoterzista').values(
            'id', 'nome', 'contoterzista__nome'
        ).order_by('nome')
        
        # Calcola superficie per ogni cascina
        data = []
        for cascina in cascine:
            cascina_obj = Cascina.objects.get(id=cascina['id'])
            superficie_totale = sum(terreno.superficie for terreno in cascina_obj.terreni.all())
            
            data.append({
                'id': cascina['id'],
                'nome': cascina['nome'],
                'superficie_totale': float(superficie_totale),
                'contoterzista': cascina['contoterzista__nome']
            })
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_terreni_by_cascina(request, cascina_id):
    """API per ottenere i terreni di una cascina"""
    try:
        terreni = Terreno.objects.filter(cascina_id=cascina_id).select_related('cascina').values(
            'id', 'nome', 'superficie', 'cascina__nome'
        ).order_by('nome')
        
        # Rinomina cascina__nome in cascina_nome per JavaScript
        terreni_list = []
        for terreno in terreni:
            terreno_data = dict(terreno)
            terreno_data['cascina_nome'] = terreno_data.pop('cascina__nome')
            terreni_list.append(terreno_data)
        
        return JsonResponse(terreni_list, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_cascina_contoterzista(request, cascina_id):
    """API per ottenere il contoterzista di una cascina"""
    try:
        cascina = get_object_or_404(Cascina.objects.select_related('contoterzista'), id=cascina_id)
        
        data = {
            'cascina': {
                'id': cascina.id,
                'nome': cascina.nome
            },
            'contoterzista': {
                'id': cascina.contoterzista.id,
                'nome': cascina.contoterzista.nome
            } if cascina.contoterzista else None
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_create_trattamento(request):
    """API per creare un nuovo trattamento (ora gestisce anche selezioni multiple)"""
    try:
        with transaction.atomic():
            # Parsing dei dati
            cliente_id = request.POST.get('cliente')
            cascina_id = request.POST.get('cascina') or None
            livello_applicazione = request.POST.get('livello_applicazione', 'cliente')
            data_esecuzione_prevista = request.POST.get('data_esecuzione_prevista') or None
            note = request.POST.get('note', '')
            
            # Validazione
            if not cliente_id:
                return JsonResponse({
                    'success': False, 
                    'error': 'Cliente è obbligatorio'
                }, status=400)
            
            # Parsing dei prodotti
            try:
                prodotti_data = json.loads(request.POST.get('prodotti_data', '[]'))
            except:
                return JsonResponse({
                    'success': False, 
                    'error': 'Dati prodotti non validi'
                }, status=400)
            
            if not prodotti_data:
                return JsonResponse({
                    'success': False, 
                    'error': 'È necessario specificare almeno un prodotto'
                }, status=400)
            
            # Creazione del trattamento
            trattamento = Trattamento.objects.create(
                cliente_id=cliente_id,
                cascina_id=cascina_id,
                livello_applicazione=livello_applicazione,
                data_esecuzione_prevista=data_esecuzione_prevista,
                note=note,
                stato='programmato'
            )
            
            # Aggiungi terreni se specificati (per selezioni multiple di terreni)
            terreni_selezionati = request.POST.getlist('terreni_selezionati')
            if terreni_selezionati:
                # Verifica che tutti i terreni esistano e appartengano alla cascina corretta
                terreni_validi = Terreno.objects.filter(
                    id__in=terreni_selezionati
                )
                
                # Se è specificata una cascina, verifica che i terreni appartengano a quella cascina
                if cascina_id:
                    terreni_validi = terreni_validi.filter(cascina_id=cascina_id)
                
                if terreni_validi.count() != len(terreni_selezionati):
                    return JsonResponse({
                        'success': False, 
                        'error': 'Alcuni terreni selezionati non sono validi'
                    }, status=400)
                
                trattamento.terreni.set(terreni_validi)
            
            # Aggiungi prodotti
            for prodotto_data in prodotti_data:
                try:
                    TrattamentoProdotto.objects.create(
                        trattamento=trattamento,
                        prodotto_id=prodotto_data['prodotto_id'],
                        quantita=prodotto_data['quantita']
                    )
                except KeyError as e:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Dati prodotto incompleti: manca {str(e)}'
                    }, status=400)
                except Exception as e:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Errore nell\'aggiunta del prodotto: {str(e)}'
                    }, status=400)
            
            # Calcola informazioni aggiuntive per la risposta
            superficie_interessata = trattamento.get_superficie_interessata()
            contoterzista = trattamento.get_contoterzista()
            
            return JsonResponse({
                'success': True, 
                'trattamento_id': trattamento.id,
                'message': 'Trattamento creato con successo',
                'dettagli': {
                    'livello_applicazione': trattamento.livello_applicazione,
                    'superficie_interessata': float(superficie_interessata),
                    'contoterzista': contoterzista.nome if contoterzista else None,
                    'prodotti_count': trattamento.trattamentoprodotto_set.count(),
                    'terreni_count': trattamento.terreni.count() if livello_applicazione == 'terreno' else 0
                }
            })
            
    except Cliente.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Cliente non trovato'
        }, status=404)
    except Cascina.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Cascina non trovata'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Errore durante la creazione: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_update_trattamento_stato(request, trattamento_id):
    """API per aggiornare lo stato di un trattamento"""
    try:
        trattamento = get_object_or_404(Trattamento, id=trattamento_id)
        nuovo_stato = request.POST.get('stato')
        
        if nuovo_stato not in [choice[0] for choice in Trattamento.STATI_CHOICES]:
            return JsonResponse({
                'success': False, 
                'error': 'Stato non valido'
            }, status=400)
        
        trattamento.stato = nuovo_stato
        trattamento.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Stato aggiornato a: {trattamento.get_stato_display()}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

def api_trattamento_detail(request, trattamento_id):
    """API per ottenere i dettagli di un trattamento"""
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
                    'quantita': float(tp.quantita),
                    'unita_misura': tp.prodotto.unita_misura
                } for tp in trattamento.trattamentoprodotto_set.all()
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)