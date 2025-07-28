# domenico/api_views.py
# API aggiuntive per la gestione del database

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import json
import logging

from .models import Cliente, Cascina, Terreno, Contoterzista, Prodotto, PrincipioAttivo, ContattoEmail

logger = logging.getLogger(__name__)

# ============ API CLIENTI ============

@require_http_methods(["GET"])
def api_clienti_list(request):
    """API per ottenere la lista dei clienti"""
    try:
        clienti = Cliente.objects.all().order_by('nome')
        
        clienti_data = []
        for cliente in clienti:
            clienti_data.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'creato_il': cliente.creato_il.isoformat() if cliente.creato_il else None,
                'superficie_totale': float(cliente.get_superficie_totale()),
                'cascine_count': cliente.cascine.count(),
                'terreni_count': sum(cascina.terreni.count() for cascina in cliente.cascine.all())
            })
        
        return JsonResponse({
            'success': True,
            'clienti': clienti_data,
            'count': len(clienti_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero clienti: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel recupero dei clienti'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_clienti_create(request):
    """API per creare un nuovo cliente"""
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
            
        # Verifica se esiste già un cliente con lo stesso nome
        if Cliente.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un cliente con il nome "{nome}"'
            }, status=400)
        
        with transaction.atomic():
            cliente = Cliente.objects.create(
                nome=nome
            )
            
            logger.info(f"Cliente creato: {cliente.nome} (ID: {cliente.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Cliente creato con successo',
                'cliente': {
                    'id': cliente.id,
                    'nome': cliente.nome,
                    'creato_il': cliente.creato_il.isoformat()
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione cliente: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del cliente'
        }, status=500)

# ============ API CASCINE ============

@require_http_methods(["GET"])
def api_cascine_list(request):
    """API per ottenere la lista delle cascine"""
    try:
        cascine = Cascina.objects.select_related('cliente', 'contoterzista').prefetch_related('terreni').all().order_by('nome')
        
        cascine_data = []
        for cascina in cascine:
            superficie_totale = sum(terreno.superficie for terreno in cascina.terreni.all())
            
            cascine_data.append({
                'id': cascina.id,
                'nome': cascina.nome,
                'cliente': {
                    'id': cascina.cliente.id,
                    'nome': cascina.cliente.nome
                },
                'contoterzista': {
                    'id': cascina.contoterzista.id,
                    'nome': cascina.contoterzista.nome
                } if cascina.contoterzista else None,
                'superficie_totale': float(superficie_totale),
                'terreni_count': cascina.terreni.count()
            })
        
        return JsonResponse({
            'success': True,
            'cascine': cascine_data,
            'count': len(cascine_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero cascine: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel recupero delle cascine'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_cascine_create(request):
    """API per creare una nuova cascina"""
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
        
        # Verifica se esiste già una cascina con lo stesso nome per lo stesso cliente
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
            
            logger.info(f"Cascina creata: {cascina.nome} per cliente {cliente.nome} (ID: {cascina.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Cascina creata con successo',
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
        logger.error(f"Errore nella creazione cascina: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione della cascina'
        }, status=500)

# ============ API TERRENI ============

@require_http_methods(["GET"])
def api_terreni_list(request):
    """API per ottenere la lista dei terreni"""
    try:
        terreni = Terreno.objects.select_related('cascina', 'cascina__cliente').all().order_by('cascina__cliente__nome', 'cascina__nome', 'nome')
        
        terreni_data = []
        for terreno in terreni:
            terreni_data.append({
                'id': terreno.id,
                'nome': terreno.nome,
                'superficie': float(terreno.superficie),
                'cascina': {
                    'id': terreno.cascina.id,
                    'nome': terreno.cascina.nome,
                    'cliente': {
                        'id': terreno.cascina.cliente.id,
                        'nome': terreno.cascina.cliente.nome
                    }
                }
            })
        
        return JsonResponse({
            'success': True,
            'terreni': terreni_data,
            'count': len(terreni_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero terreni: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel recupero dei terreni'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_terreni_create(request):
    """API per creare un nuovo terreno"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        cascina_id = data.get('cascina_id')
        nome = data.get('nome', '').strip()
        superficie = data.get('superficie')
        
        # Validazione
        if not cascina_id:
            return JsonResponse({
                'success': False,
                'error': 'La cascina è obbligatoria'
            }, status=400)
            
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome del terreno è obbligatorio'
            }, status=400)
            
        if not superficie:
            return JsonResponse({
                'success': False,
                'error': 'La superficie è obbligatoria'
            }, status=400)
        
        try:
            superficie = float(superficie)
            if superficie <= 0:
                raise ValueError("La superficie deve essere maggiore di zero")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'La superficie deve essere un numero valido maggiore di zero'
            }, status=400)
        
        # Verifica che la cascina esista
        try:
            cascina = Cascina.objects.select_related('cliente').get(id=cascina_id)
        except Cascina.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cascina non trovata'
            }, status=404)
        
        # Verifica se esiste già un terreno con lo stesso nome nella stessa cascina
        if Terreno.objects.filter(cascina=cascina, nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'La cascina "{cascina.nome}" ha già un terreno chiamato "{nome}"'
            }, status=400)
        
        with transaction.atomic():
            terreno = Terreno.objects.create(
                cascina=cascina,
                nome=nome,
                superficie=superficie
            )
            
            logger.info(f"Terreno creato: {terreno.nome} in cascina {cascina.nome} (ID: {terreno.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Terreno creato con successo',
                'terreno': {
                    'id': terreno.id,
                    'nome': terreno.nome,
                    'superficie': float(terreno.superficie),
                    'cascina': terreno.cascina.nome,
                    'cliente': terreno.cascina.cliente.nome
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione terreno: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del terreno'
        }, status=500)

# ============ API CONTOTERZISTI ============

@require_http_methods(["GET"])
def api_contoterzisti_list(request):
    """API per ottenere la lista dei contoterzisti"""
    try:
        contoterzisti = Contoterzista.objects.all().order_by('nome')
        
        contoterzisti_data = []
        for contoterzista in contoterzisti:
            contoterzisti_data.append({
                'id': contoterzista.id,
                'nome': contoterzista.nome,
                'telefono': contoterzista.telefono,
                'email': contoterzista.email,
                'cascine_count': contoterzista.cascine.count()
            })
        
        return JsonResponse({
            'success': True,
            'contoterzisti': contoterzisti_data,
            'count': len(contoterzisti_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero contoterzisti: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel recupero dei contoterzisti'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_contoterzisti_create(request):
    """API per creare un nuovo contoterzista"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        nome = data.get('nome', '').strip()
        telefono = data.get('telefono', '').strip()
        email = data.get('email', '').strip()
        
        # Validazione
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome è obbligatorio'
            }, status=400)
            
        if not telefono:
            return JsonResponse({
                'success': False,
                'error': 'Il telefono è obbligatorio'
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
                telefono=telefono,
                email=email
            )
            
            logger.info(f"Contoterzista creato: {contoterzista.nome} (ID: {contoterzista.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Contoterzista creato con successo',
                'contoterzista': {
                    'id': contoterzista.id,
                    'nome': contoterzista.nome,
                    'telefono': contoterzista.telefono,
                    'email': contoterzista.email
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione contoterzista: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del contoterzista'
        }, status=500)

# ============ API PRODOTTI ============

@require_http_methods(["GET"])
def api_prodotti_list(request):
    """API per ottenere la lista dei prodotti"""
    try:
        prodotti = Prodotto.objects.prefetch_related('principi_attivi').all().order_by('nome')
        
        prodotti_data = []
        for prodotto in prodotti:
            prodotti_data.append({
                'id': prodotto.id,
                'nome': prodotto.nome,
                'unita_misura': prodotto.unita_misura,
                'descrizione': prodotto.descrizione,
                'principi_attivi': prodotto.get_principi_attivi_list()
            })
        
        return JsonResponse({
            'success': True,
            'prodotti': prodotti_data,
            'count': len(prodotti_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel recupero prodotti: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel recupero dei prodotti'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_prodotti_create(request):
    """API per creare un nuovo prodotto"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        nome = data.get('nome', '').strip()
        unita_misura = data.get('unita_misura', '').strip()
        principi_attivi_str = data.get('principi_attivi', '').strip()
        descrizione = data.get('descrizione', '').strip()
        
        # Validazione
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Il nome del prodotto è obbligatorio'
            }, status=400)
            
        if not unita_misura:
            return JsonResponse({
                'success': False,
                'error': 'L\'unità di misura è obbligatoria'
            }, status=400)
        
        # Verifica se esiste già un prodotto con lo stesso nome
        if Prodotto.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un prodotto con il nome "{nome}"'
            }, status=400)
        
        with transaction.atomic():
            prodotto = Prodotto.objects.create(
                nome=nome,
                unita_misura=unita_misura,
                descrizione=descrizione
            )
            
            # Gestione principi attivi
            if principi_attivi_str:
                principi_nomi = [pa.strip() for pa in principi_attivi_str.split(',') if pa.strip()]
                for pa_nome in principi_nomi:
                    principio_attivo, created = PrincipioAttivo.objects.get_or_create(
                        nome=pa_nome
                    )
                    prodotto.principi_attivi.add(principio_attivo)
            
            logger.info(f"Prodotto creato: {prodotto.nome} (ID: {prodotto.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'Prodotto creato con successo',
                'prodotto': {
                    'id': prodotto.id,
                    'nome': prodotto.nome,
                    'unita_misura': prodotto.unita_misura,
                    'descrizione': prodotto.descrizione,
                    'principi_attivi': prodotto.get_principi_attivi_list()
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione prodotto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del prodotto'
        }, status=500)

# ============ API CONTATTI EMAIL ============

@csrf_exempt
@require_http_methods(["POST"])
def api_contatti_email_create(request, cliente_id):
    """API per creare un nuovo contatto email per un cliente"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        ruolo = data.get('ruolo', '').strip()
        telefono = data.get('telefono', '').strip()
        priorita = data.get('priorita', 2)
        attivo = data.get('attivo', True)
        note = data.get('note', '').strip()
        
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
        
        # Verifica che il cliente esista
        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cliente non trovato'
            }, status=404)
        
        # Verifica se esiste già un contatto con la stessa email per questo cliente
        if ContattoEmail.objects.filter(cliente=cliente, email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un contatto con l\'email "{email}" per questo cliente'
            }, status=400)
        
        try:
            priorita = int(priorita)
        except (ValueError, TypeError):
            priorita = 2
            
        if isinstance(attivo, str):
            attivo = attivo.lower() == 'true'
        
        with transaction.atomic():
            contatto = ContattoEmail.objects.create(
                cliente=cliente,
                nome=nome,
                email=email,
                ruolo=ruolo,
                telefono=telefono,
                priorita=priorita,
                attivo=attivo,
                note=note
            )
            
            logger.info(f"Contatto email creato: {contatto.nome} ({contatto.email}) per cliente {cliente.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Contatto creato con successo',
                'contatto': {
                    'id': contatto.id,
                    'nome': contatto.nome,
                    'email': contatto.email,
                    'ruolo': contatto.ruolo,
                    'telefono': contatto.telefono,
                    'priorita': contatto.priorita,
                    'attivo': contatto.attivo,
                    'note': contatto.note,
                    'cliente': contatto.cliente.nome
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione contatto email: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del contatto'
        }, status=500)