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

# ============ AGGIORNAMENTO API TRATTAMENTI ============

@csrf_exempt
@require_http_methods(["POST"])
def api_create_trattamento(request):
    """API per creare un nuovo trattamento con quantità per ettaro"""
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
            
            # Parsing dei prodotti con quantità per ettaro
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
            
            # Validazione dei prodotti - ora aspettiamo quantita_per_ettaro
            for prodotto_data in prodotti_data:
                if 'quantita_per_ettaro' not in prodotto_data:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Ogni prodotto deve avere quantita_per_ettaro specificata'
                    }, status=400)
                
                try:
                    float(prodotto_data['quantita_per_ettaro'])
                except ValueError:
                    return JsonResponse({
                        'success': False, 
                        'error': 'La quantità per ettaro deve essere un numero valido'
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
            
            # Aggiungi prodotti con quantità per ettaro
            prodotti_creati = []
            for prodotto_data in prodotti_data:
                try:
                    trattamento_prodotto = TrattamentoProdotto.objects.create(
                        trattamento=trattamento,
                        prodotto_id=prodotto_data['prodotto_id'],
                        quantita_per_ettaro=prodotto_data['quantita_per_ettaro']  # Ora salviamo per ettaro
                    )
                    prodotti_creati.append({
                        'prodotto_nome': trattamento_prodotto.prodotto.nome,
                        'quantita_per_ettaro': float(trattamento_prodotto.quantita_per_ettaro),
                        'quantita_totale': float(trattamento_prodotto.quantita_totale),
                        'unita_misura': trattamento_prodotto.prodotto.unita_misura
                    })
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
                    'terreni_count': trattamento.terreni.count() if livello_applicazione == 'terreno' else 0,
                    'prodotti_dettagli': prodotti_creati
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