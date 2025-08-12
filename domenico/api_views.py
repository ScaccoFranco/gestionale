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
from django.core.paginator import Paginator
from datetime import timedelta

from .activity_logging import (
    log_cliente_created, log_terreno_created, log_prodotto_created,
    log_contoterzista_created, log_contatto_created, log_trattamento_created,
    log_comunicazione_sent, log_cascina_created
)
# Import delle funzioni email
from .email_utils import (
    send_trattamento_communication
)

from .models import *

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
    """API per creare nuovo cliente con contatti e logging"""
    try:
        print("🔍 DEBUG: api_clienti_create chiamata")
        print(f"Content-Type: {request.content_type}")
        print(f"POST data: {dict(request.POST)}")
        
        # Gestisci sia JSON che FormData
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            print(f"JSON data: {data}")
        else:
            data = request.POST
            print(f"Form data: {dict(data)}")
            
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
            print(f"✅ Cliente creato: {cliente.nome} (ID: {cliente.id})")
            
            # 🔥 NUOVO: Log dell'attività
            log_cliente_created(cliente, request)
            print(f"✅ Log cliente creato")
            
            # Gestisci contatti se presenti
            contatti = data.get('contatti', [])
            contatti_creati = 0
            
            print(f"📧 Contatti da creare: {len(contatti)}")
            
            for contatto_data in contatti:
                print(f"Processando contatto: {contatto_data}")
                if contatto_data.get('nome') and contatto_data.get('email'):
                    try:
                        contatto = ContattoEmail.objects.create(
                            cliente=cliente,
                            nome=contatto_data['nome'],
                            email=contatto_data['email']
                        )
                        contatti_creati += 1
                        
                        # Log anche per ogni contatto
                        log_contatto_created(contatto, request)
                        print(f"✅ Contatto creato e loggato: {contatto.nome}")
                        
                    except Exception as e:
                        print(f"❌ Errore creazione contatto: {e}")
            
            print(f"✅ Totale contatti creati: {contatti_creati}")
            
            return JsonResponse({
                'success': True,
                'message': f'Cliente "{nome}" creato con successo',
                'cliente': {
                    'id': cliente.id,
                    'nome': cliente.nome,
                    'contatti_count': contatti_creati
                },
                'contatti_creati': contatti_creati
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        print(f"❌ Errore generale nella creazione cliente: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Errore nella creazione del cliente: {str(e)}'
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
    """API per creare una nuova cascina con logging"""
    try:
        print(f"🔍 DEBUG Cascina - Content-Type: {request.content_type}")
        
        # Parse JSON data o form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            print(f"🔍 DEBUG Cascina - JSON data: {data}")
        else:
            data = request.POST
            print(f"🔍 DEBUG Cascina - Form data: {dict(data)}")
            
        cliente_id = data.get('cliente_id')
        nome = data.get('nome', '').strip()
        contoterzista_id = data.get('contoterzista_id') or None
        
        print(f"🔍 DEBUG Cascina - Parsed: cliente_id={cliente_id}, nome='{nome}', contoterzista_id={contoterzista_id}")
        
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
        
        contoterzista = None
        if contoterzista_id:
            try:
                contoterzista = Contoterzista.objects.get(id=contoterzista_id)
            except Contoterzista.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Contoterzista non trovato'
                }, status=404)
        
        # Verifica che non esista già una cascina con lo stesso nome per questo cliente
        if Cascina.objects.filter(cliente=cliente, nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già una cascina chiamata "{nome}" per questo cliente'
            }, status=400)
        
        with transaction.atomic():
            cascina = Cascina.objects.create(
                nome=nome,
                cliente=cliente,
                contoterzista=contoterzista
            )
            
            print(f"✅ Cascina creata: {cascina.nome} (ID: {cascina.id})")
            
            # 🔥 Log dell'attività
            try:
                log_cascina_created(cascina, request)
                print(f"✅ Log cascina creato con successo")
            except Exception as log_error:
                logger.error(f"Errore nel logging cascina: {str(log_error)}")
                print(f"❌ Errore nel logging: {log_error}")
                # Non bloccare la creazione se il log fallisce
            
            return JsonResponse({
                'success': True,
                'message': 'Cascina creata con successo',
                'cascina': {
                    'id': cascina.id,
                    'nome': cascina.nome,
                    'cliente_id': cliente.id,
                    'cliente_nome': cliente.nome,
                    'contoterzista_nome': contoterzista.nome if contoterzista else None
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        logger.error(f"Errore nella creazione cascina: {str(e)}")
        print(f"❌ Errore generale nella creazione cascina: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        with transaction.atomic():
            contatto = ContattoEmail.objects.create(
                cliente=cliente,
                nome=nome,
                email=email,
            )
            
            logger.info(f"Contatto email creato: {contatto.nome} ({contatto.email}) per cliente {cliente.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Contatto creato con successo',
                'contatto': {
                    'id': contatto.id,
                    'nome': contatto.nome,
                    'email': contatto.email,
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
    

@csrf_exempt
@require_http_methods(["POST"])
def api_terreni_create(request):
    """API per creare un nuovo terreno"""
    try:
        # Ottieni dati dal form
        cascina_id = request.POST.get('cascina_id')
        nome = request.POST.get('nome', '').strip()
        superficie = request.POST.get('superficie')
        
        # Validazione
        if not cascina_id:
            return JsonResponse({
                'success': False,
                'error': 'ID cascina è obbligatorio'
            }, status=400)
            
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Nome terreno è obbligatorio'
            }, status=400)
            
        if not superficie:
            return JsonResponse({
                'success': False,
                'error': 'Superficie è obbligatoria'
            }, status=400)
        
        # Converti superficie a decimale
        try:
            superficie_decimal = float(superficie)
            if superficie_decimal <= 0:
                raise ValueError("Superficie deve essere positiva")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Superficie deve essere un numero positivo'
            }, status=400)
        
        # Verifica che la cascina esista
        cascina = get_object_or_404(Cascina, id=cascina_id)
        
        # Verifica che non esista già un terreno con lo stesso nome nella cascina
        if Terreno.objects.filter(cascina=cascina, nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un terreno chiamato "{nome}" in questa cascina'
            }, status=400)
        
        # Crea il terreno
        with transaction.atomic():
            terreno = Terreno.objects.create(
                nome=nome,
                cascina=cascina,
                superficie=superficie_decimal
            )
            
            logger.info(f"Terreno creato: {terreno.nome} ({terreno.superficie} ha) - {cascina.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Terreno creato con successo',
                'terreno': {
                    'id': terreno.id,
                    'nome': terreno.nome,
                    'superficie': float(terreno.superficie),
                    'cascina_id': cascina.id,
                    'cascina_nome': cascina.nome,
                    'cliente_nome': cascina.cliente.nome
                }
            })
            
    except Cascina.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cascina non trovata'
        }, status=404)
    except Exception as e:
        logger.error(f"Errore nella creazione terreno: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del terreno'
        }, status=500)

# ============ API PRODOTTI ============

@csrf_exempt
@require_http_methods(["POST"])
def api_prodotti_create(request):
    """API per creare un nuovo prodotto con principi attivi"""
    try:
        # Ottieni dati dal form
        nome = request.POST.get('nome', '').strip()
        unita_misura = request.POST.get('unita_misura', '').strip()
        descrizione = request.POST.get('descrizione', '').strip()
        principi_attivi_json = request.POST.get('principi_attivi', '[]')
        
        # Validazione base
        if not nome:
            return JsonResponse({
                'success': False,
                'error': 'Nome prodotto è obbligatorio'
            }, status=400)
            
        if not unita_misura:
            return JsonResponse({
                'success': False,
                'error': 'Unità di misura è obbligatoria'
            }, status=400)
        
        # Parse principi attivi
        try:
            principi_attivi_nomi = json.loads(principi_attivi_json)
            if not isinstance(principi_attivi_nomi, list) or len(principi_attivi_nomi) == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Almeno un principio attivo è obbligatorio'
                }, status=400)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Formato principi attivi non valido'
            }, status=400)
        
        # Verifica che non esista già un prodotto con lo stesso nome
        if Prodotto.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un prodotto chiamato "{nome}"'
            }, status=400)
        
        # Crea prodotto e principi attivi
        with transaction.atomic():
            # Crea il prodotto
            prodotto = Prodotto.objects.create(
                nome=nome,
                unita_misura=unita_misura,
                descrizione=descrizione
            )
            
            # Crea o ottieni principi attivi e associali al prodotto
            principi_attivi_creati = []
            for principio_nome in principi_attivi_nomi:
                principio_nome = principio_nome.strip()
                if principio_nome:
                    principio, created = PrincipioAttivo.objects.get_or_create(
                        nome__iexact=principio_nome,
                        defaults={'nome': principio_nome}
                    )
                    prodotto.principi_attivi.add(principio)
                    principi_attivi_creati.append({
                        'id': principio.id,
                        'nome': principio.nome,
                        'created': created
                    })
            
            logger.info(f"Prodotto creato: {prodotto.nome} con {len(principi_attivi_creati)} principi attivi")
            
            return JsonResponse({
                'success': True,
                'message': 'Prodotto creato con successo',
                'prodotto': {
                    'id': prodotto.id,
                    'nome': prodotto.nome,
                    'unita_misura': prodotto.unita_misura,
                    'descrizione': prodotto.descrizione,
                    'principi_attivi': principi_attivi_creati
                }
            })
            
    except Exception as e:
        logger.error(f"Errore nella creazione prodotto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del prodotto'
        }, status=500)


@require_http_methods(["GET"])
def api_clienti_list(request):
    """API per ottenere la lista dei clienti"""
    try:
        clienti = Cliente.objects.all().order_by('nome').values('id', 'nome')
        return JsonResponse(list(clienti), safe=False)
    except Exception as e:
        logger.error(f"Errore nel caricamento clienti: {str(e)}")
        return JsonResponse({'error': 'Errore nel caricamento clienti'}, status=500)

@require_http_methods(["GET"])
def api_principi_attivi_list(request):
    """API per ottenere la lista dei principi attivi (per autocomplete)"""
    try:
        query = request.GET.get('q', '').strip()
        
        principi = PrincipioAttivo.objects.all()
        
        if query:
            principi = principi.filter(nome__icontains=query)
        
        principi_data = list(principi.order_by('nome').values('id', 'nome')[:20])
        
        return JsonResponse({
            'success': True,
            'principi_attivi': principi_data
        })
    except Exception as e:
        logger.error(f"Errore nel caricamento principi attivi: {str(e)}")
        return JsonResponse({'error': 'Errore nel caricamento principi attivi'}, status=500)

# ============ API STATS AGGIORNATE ============

@require_http_methods(["GET"])
def api_database_stats(request):
    """API per ottenere statistiche aggiornate del database"""
    try:
        stats = {
            'clienti': Cliente.objects.count(),
            'cascine': Cascina.objects.count(),
            'terreni': Terreno.objects.count(),
            'contoterzisti': Contoterzista.objects.count(),
            'prodotti': Prodotto.objects.count(),
            'principi_attivi': PrincipioAttivo.objects.count(),
        }
        
        # Calcola superficie totale
        from django.db.models import Sum
        superficie_totale = Terreno.objects.aggregate(
            totale=Sum('superficie')
        )['totale'] or 0
        
        stats['superficie_totale'] = float(superficie_totale)
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Errore nel caricamento statistiche: {str(e)}")
        return JsonResponse({'error': 'Errore nel caricamento statistiche'}, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def api_terreni_create(request):
    """API per creare un nuovo terreno con logging"""
    try:
        # ... codice di validazione esistente ...
        cascina_id = request.POST.get('cascina_id')
        nome = request.POST.get('nome', '').strip()
        superficie = request.POST.get('superficie')
        
        # Validazione (mantieni quella esistente)
        if not all([cascina_id, nome, superficie]):
            return JsonResponse({
                'success': False,
                'error': 'Tutti i campi sono obbligatori'
            }, status=400)
        
        try:
            superficie_decimal = float(superficie)
            if superficie_decimal <= 0:
                raise ValueError("Superficie deve essere positiva")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Superficie deve essere un numero positivo'
            }, status=400)
        
        cascina = get_object_or_404(Cascina, id=cascina_id)
        
        if Terreno.objects.filter(cascina=cascina, nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un terreno chiamato "{nome}" in questa cascina'
            }, status=400)
        
        # Crea il terreno
        with transaction.atomic():
            terreno = Terreno.objects.create(
                nome=nome,
                cascina=cascina,
                superficie=superficie_decimal
            )
            
            # 🔥 NUOVO: Log dell'attività
            log_terreno_created(terreno, request)
            
            logger.info(f"Terreno creato con logging: {terreno.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Terreno creato con successo',
                'terreno': {
                    'id': terreno.id,
                    'nome': terreno.nome,
                    'superficie': float(terreno.superficie),
                    'cascina_id': cascina.id,
                    'cascina_nome': cascina.nome,
                    'cliente_nome': cascina.cliente.nome
                }
            })
            
    except Exception as e:
        logger.error(f"Errore nella creazione terreno: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del terreno'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_prodotti_create(request):
    """API per creare un nuovo prodotto con logging"""
    try:
        # ... codice di validazione esistente ...
        nome = request.POST.get('nome', '').strip()
        unita_misura = request.POST.get('unita_misura', '').strip()
        descrizione = request.POST.get('descrizione', '').strip()
        principi_attivi_json = request.POST.get('principi_attivi', '[]')
        
        # Validazione (mantieni quella esistente)
        if not all([nome, unita_misura]):
            return JsonResponse({
                'success': False,
                'error': 'Nome prodotto e unità di misura sono obbligatori'
            }, status=400)
        
        try:
            principi_attivi_nomi = json.loads(principi_attivi_json)
            if not isinstance(principi_attivi_nomi, list) or len(principi_attivi_nomi) == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Almeno un principio attivo è obbligatorio'
                }, status=400)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Formato principi attivi non valido'
            }, status=400)
        
        if Prodotto.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un prodotto chiamato "{nome}"'
            }, status=400)
        
        # Crea prodotto e principi attivi
        with transaction.atomic():
            prodotto = Prodotto.objects.create(
                nome=nome,
                unita_misura=unita_misura,
                descrizione=descrizione
            )
            
            principi_attivi_creati = []
            for principio_nome in principi_attivi_nomi:
                principio_nome = principio_nome.strip()
                if principio_nome:
                    principio, created = PrincipioAttivo.objects.get_or_create(
                        nome__iexact=principio_nome,
                        defaults={'nome': principio_nome}
                    )
                    prodotto.principi_attivi.add(principio)
                    principi_attivi_creati.append(principio)
            
            # 🔥 NUOVO: Log dell'attività
            log_prodotto_created(prodotto, principi_attivi_creati, request)
            
            logger.info(f"Prodotto creato con logging: {prodotto.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Prodotto creato con successo',
                'prodotto': {
                    'id': prodotto.id,
                    'nome': prodotto.nome,
                    'unita_misura': prodotto.unita_misura,
                    'descrizione': prodotto.descrizione,
                    'principi_attivi': [pa.nome for pa in principi_attivi_creati]
                }
            })
            
    except Exception as e:
        logger.error(f"Errore nella creazione prodotto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del prodotto'
        }, status=500)
@csrf_exempt
@require_http_methods(["POST"])
def api_contoterzisti_create(request):
    """API per creare un nuovo contoterzista con logging"""
    try:
        # Parse JSON data o form data
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
                'error': 'Nome contoterzista è obbligatorio'
            }, status=400)
        
        if email:
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email):
                return JsonResponse({
                    'success': False,
                    'error': 'Indirizzo email non valido'
                }, status=400)
            
            if Contoterzista.objects.filter(email__iexact=email).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Esiste già un contoterzista con email "{email}"'
                }, status=400)
        
        if Contoterzista.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({
                'success': False,
                'error': f'Esiste già un contoterzista chiamato "{nome}"'
            }, status=400)
        
        # Crea il contoterzista
        with transaction.atomic():
            contoterzista = Contoterzista.objects.create(
                nome=nome,
                email=email
            )
            
            # 🔥 Log dell'attività
            log_contoterzista_created(contoterzista, request)
            
            logger.info(f"Contoterzista creato con logging: {contoterzista.nome}")
            
            return JsonResponse({
                'success': True,
                'message': 'Contoterzista creato con successo',
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
        logger.error(f"Errore nella creazione contoterzista: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del contoterzista'
        }, status=500)
# ============ AGGIORNA ANCHE API CONTATTI ESISTENTI ============

@csrf_exempt
@require_http_methods(["POST"])
def api_add_contatto_cliente(request, cliente_id):
    """API per aggiungere un contatto email con logging"""
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
        
        # Dopo la creazione del contatto, aggiungi:
        with transaction.atomic():
            contatto = ContattoEmail.objects.create(
                cliente=cliente,
                nome=nome,
                email=email,
            )
            
            # 🔥 NUOVO: Log dell'attività
            log_contatto_created(contatto, request)
            
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
            
    except Exception as e:
        logger.error(f"Errore nella creazione contatto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'aggiunta del contatto: {str(e)}'
        }, status=500)
    


# ============ API PER ATTIVITÀ RECENTI ============

@require_http_methods(["GET"])
def api_recent_activities(request):
    """API per ottenere le attività recenti"""
    try:
        # Parametri di filtro
        days = int(request.GET.get('days', 7))
        limit = int(request.GET.get('limit', 10))
        activity_type = request.GET.get('type', '')
        
        # Calcola data limite
        data_limite = timezone.now() - timedelta(days=days)
        
        # Query base
        activities = ActivityLog.objects.filter(timestamp__gte=data_limite)
        
        # Filtro per tipo se specificato
        if activity_type:
            activities = activities.filter(activity_type=activity_type)
        
        # Limita risultati
        activities = activities.order_by('-timestamp')[:limit]
        
        # Serializza i dati
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'type': activity.activity_type,
                'type_display': activity.get_activity_type_display(),
                'title': activity.title,
                'description': activity.description,
                'timestamp': activity.timestamp.isoformat(),
                'time_since': activity.time_since(),
                'icon': activity.get_icon(),
                'color_class': activity.get_color_class(),
                'related_object': {
                    'type': activity.related_object_type,
                    'id': activity.related_object_id,
                    'name': activity.related_object_name
                } if activity.related_object_type else None,
                'extra_data': activity.extra_data
            })
        
        return JsonResponse({
            'success': True,
            'activities': activities_data,
            'count': len(activities_data)
        })
        
    except Exception as e:
        logger.error(f"Errore nel caricamento attività recenti: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel caricamento delle attività'
        }, status=500)

# ============ API PER STATISTICHE DASHBOARD ============

@require_http_methods(["GET"])
def api_dashboard_summary(request):
    """API per ottenere riepilogo completo della dashboard"""
    try:
        from datetime import datetime, timedelta
        from django.db.models import Count, Sum
        
        # Statistiche base
        stats = {
            'clienti_totali': Cliente.objects.count(),
            'cascine_totali': Cascina.objects.count(),
            'terreni_totali': Terreno.objects.count(),
            'superficie_totale': float(Terreno.objects.aggregate(
                totale=Sum('superficie')
            )['totale'] or 0),
            'trattamenti_programmati': Trattamento.objects.filter(stato='programmato').count(),
            'trattamenti_comunicati': Trattamento.objects.filter(stato='comunicati').count(),
            'prodotti_totali': Prodotto.objects.count(),
            'contoterzisti_totali': Contoterzista.objects.count(),
            'contatti_email_totali': ContattoEmail.objects.count(),
            'principi_attivi_totali': PrincipioAttivo.objects.count(),
        }
        
        # Attività recenti
        settimana_fa = timezone.now() - timedelta(days=7)
        attivita_settimana = ActivityLog.objects.filter(
            timestamp__gte=settimana_fa
        ).count()
        
        # Crescita rispetto alla settimana precedente
        due_settimane_fa = timezone.now() - timedelta(days=14)
        attivita_settimana_precedente = ActivityLog.objects.filter(
            timestamp__gte=due_settimane_fa,
            timestamp__lt=settimana_fa
        ).count()
        
        crescita_attivita = attivita_settimana - attivita_settimana_precedente
        
        # Top attività per tipo
        top_activities = list(ActivityLog.objects.filter(
            timestamp__gte=settimana_fa
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'activity_summary': {
                'attivita_settimana': attivita_settimana,
                'crescita': crescita_attivita,
                'top_activities': top_activities
            }
        })
        
    except Exception as e:
        logger.error(f"Errore nel caricamento riepilogo dashboard: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel caricamento del riepilogo'
        }, status=500)
                


@csrf_exempt
@require_http_methods(["POST"])
def api_create_trattamento(request):
    """API per creare un nuovo trattamento con gestione corretta dei prodotti"""

    from decimal import Decimal
    
    print("=== DEBUG API CREATE TRATTAMENTO ===")
    print("POST data keys:", list(request.POST.keys()))
    print("POST data:", dict(request.POST))
    
    try:
        with transaction.atomic():
            # 1. Parsing dati base
            cliente_id = request.POST.get('cliente')
            cascina_id = request.POST.get('cascina') or None
            livello_applicazione = request.POST.get('livello_applicazione', 'cliente')
            data_esecuzione = request.POST.get('data_esecuzione') or None

            print(f"Cliente ID: {cliente_id}")
            print(f"Cascina ID: {cascina_id}")
            print(f"Livello: {livello_applicazione}")
            
            # 2. Validazioni
            if not cliente_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Cliente è obbligatorio'
                }, status=400)
            
            cliente = get_object_or_404(Cliente, id=cliente_id)
            cascina = None
            
            if cascina_id:
                cascina = get_object_or_404(Cascina, id=cascina_id)
            
            # 3. Crea il trattamento
            trattamento = Trattamento.objects.create(
                cliente=cliente,
                cascina=cascina,
                livello_applicazione=livello_applicazione,
                data_esecuzione=data_esecuzione if data_esecuzione else None,
                stato='programmato'
            )
            
            print(f"✅ Trattamento creato: ID {trattamento.id}")
            
            # 4. Gestisci terreni se livello è 'terreno'
            if livello_applicazione == 'terreno':
                terreni_ids = request.POST.getlist('terreni_selezionati')
                print(f"Terreni IDS: {terreni_ids}")
                
                if terreni_ids:
                    terreni = Terreno.objects.filter(id__in=terreni_ids)
                    trattamento.terreni.set(terreni)
                    print(f"✅ Associati {terreni.count()} terreni")
            
            # 5. ⚠️ GESTIONE PRODOTTI - QUI ERA IL PROBLEMA!
            prodotti_data_str = request.POST.get('prodotti_data')
            print(f"Prodotti data raw: {prodotti_data_str}")
            
            if prodotti_data_str:
                try:
                    prodotti_data = json.loads(prodotti_data_str)
                    print(f"Prodotti parsed: {prodotti_data}")
                    
                    prodotti_creati = 0
                    for prodotto_info in prodotti_data:
                        prodotto_id = prodotto_info.get('prodotto_id')
                        quantita_per_ettaro = prodotto_info.get('quantita_per_ettaro')
                        
                        print(f"Elaboro prodotto: ID={prodotto_id}, Quantità/ha={quantita_per_ettaro}")
                        
                        if prodotto_id and quantita_per_ettaro:
                            try:
                                prodotto = Prodotto.objects.get(id=prodotto_id)
                                
                                # ✅ USA IL NOME CAMPO CORRETTO
                                trattamento_prodotto = TrattamentoProdotto.objects.create(
                                    trattamento=trattamento,
                                    prodotto=prodotto,
                                    quantita_per_ettaro=Decimal(str(quantita_per_ettaro))
                                )
                                
                                prodotti_creati += 1
                                print(f"✅ Prodotto salvato: {prodotto.nome} - {quantita_per_ettaro} {prodotto.unita_misura}/ha")
                                
                            except Prodotto.DoesNotExist:
                                print(f"❌ Prodotto non trovato: ID {prodotto_id}")
                            except Exception as e:
                                print(f"❌ Errore salvataggio prodotto {prodotto_id}: {e}")
                        else:
                            print(f"⚠️ Dati prodotto incompleti: {prodotto_info}")
                    
                    print(f"✅ Salvati {prodotti_creati} prodotti su {len(prodotti_data)} forniti")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Errore parsing JSON prodotti: {e}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Formato dati prodotti non valido'
                    }, status=400)
            else:
                print("⚠️ Nessun dato prodotti fornito")
            
            # 6. Verifica finale
            prodotti_count = trattamento.trattamentoprodotto_set.count()
            superficie = trattamento.get_superficie_interessata()
            contoterzista = trattamento.get_contoterzista()
            
            print(f"✅ TRATTAMENTO COMPLETATO:")
            print(f"   - ID: {trattamento.id}")
            print(f"   - Prodotti associati: {prodotti_count}")
            print(f"   - Superficie: {superficie} ha")
            print(f"   - Contoterzista: {contoterzista.nome if contoterzista else 'N/A'}")
            
            return JsonResponse({
                'success': True,
                'message': f'Trattamento creato con successo con {prodotti_count} prodotti',
                'trattamento_id': trattamento.id,
                'dettagli': {
                    'livello_applicazione': trattamento.livello_applicazione,
                    'superficie_interessata': float(superficie),
                    'contoterzista': contoterzista.nome if contoterzista else None,
                    'prodotti_count': prodotti_count,
                    'terreni_count': trattamento.terreni.count() if livello_applicazione == 'terreno' else 0
                }
            })
            
    except Exception as e:
        print(f"❌ ERRORE GENERALE: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la creazione: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_add_contatto_cliente(request, cliente_id):
    """API per aggiungere un contatto email con logging"""
    try:
        # Verifica che il cliente esista
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # Ottieni dati dal form
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        
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
        with transaction.atomic():
            contatto = ContattoEmail.objects.create(
                cliente=cliente,
                nome=nome,
                email=email
            )
            
            # 🔥 NUOVO: Log dell'attività
            log_contatto_created(contatto, request)
            
            print(f"✅ Contatto creato con logging: {contatto.nome}")
            
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
        print(f"❌ Errore nella creazione contatto: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'aggiunta del contatto: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_cliente_create(request):
    """API per creare nuovo cliente con logging"""
    try:
        # Parse data
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
            
            # 🔥 NUOVO: Log dell'attività
            log_cliente_created(cliente, request)
            
            # Gestisci contatti se presenti
            contatti = data.get('contatti', [])
            contatti_creati = []
            
            for contatto_data in contatti:
                if contatto_data.get('nome') and contatto_data.get('email'):
                    contatto = ContattoEmail.objects.create(
                        cliente=cliente,
                        nome=contatto_data['nome'],
                        email=contatto_data['email']
                    )
                    contatti_creati.append(contatto.nome)
                    
                    # Log anche per ogni contatto
                    log_contatto_created(contatto, request)
            
            print(f"✅ Cliente creato con logging: {cliente.nome} + {len(contatti_creati)} contatti")
            
            return JsonResponse({
                'success': True,
                'message': 'Cliente creato con successo',
                'cliente': {
                    'id': cliente.id,
                    'nome': cliente.nome,
                    'contatti_count': len(contatti_creati)
                }
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dati JSON non validi'
        }, status=400)
    except Exception as e:
        print(f"❌ Errore nella creazione cliente: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella creazione del cliente'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_send_comunicazione(request, trattamento_id):
    """API per inviare la comunicazione email con logging"""
    try:
        force_send = request.POST.get('force_send', 'false').lower() == 'true'
        
        # Ottieni il trattamento
        trattamento = get_object_or_404(Trattamento, id=trattamento_id)
        
        # Invia la comunicazione
        risultato = send_trattamento_communication(trattamento_id, force_send=force_send)
        
        if risultato['success']:
            # 🔥 NUOVO: Log dell'attività
            log_comunicazione_sent(
                trattamento, 
                risultato.get('destinatari_count', 0), 
                request
            )
            
            print(f"✅ Comunicazione inviata con logging per trattamento {trattamento_id}")
            
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
            
    except Trattamento.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Trattamento non trovato'
        }, status=404)
    except Exception as e:
        print(f"❌ Errore nell'invio comunicazione: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Errore nell\'invio della comunicazione: {str(e)}'
        }, status=500)
    

@require_http_methods(["GET"])
def api_recent_activities(request):
    """API per ottenere le attività recenti"""
    try:
        # Parametri di filtro
        days = int(request.GET.get('days', 7))
        limit = int(request.GET.get('limit', 10))
        offset = int(request.GET.get('offset', 0))
        activity_type = request.GET.get('type', '')
        
        # Calcola data limite
        data_limite = timezone.now() - timedelta(days=days)
        
        # Query base
        activities = ActivityLog.objects.filter(timestamp__gte=data_limite)
        
        # Filtro per tipo se specificato
        if activity_type and activity_type != 'all':
            activities = activities.filter(activity_type=activity_type)
        
        # Applica offset e limit
        activities = activities.order_by('-timestamp')[offset:offset+limit]
        
        # Serializza i dati
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'type': activity.activity_type,
                'type_display': activity.get_activity_type_display(),
                'title': activity.title,
                'description': activity.description,
                'timestamp': activity.timestamp.isoformat(),
                'time_since': activity.time_since(),
                'icon': activity.get_icon(),
                'color_class': activity.get_color_class(),
                'related_object': {
                    'type': activity.related_object_type,
                    'id': activity.related_object_id,
                    'name': activity.related_object_name
                } if activity.related_object_type else None,
                'extra_data': activity.extra_data
            })
        
        return JsonResponse({
            'success': True,
            'activities': activities_data,
            'count': len(activities_data),
            'has_more': len(activities_data) == limit  # Indica se ci sono più attività
        })
        
    except Exception as e:
        logger.error(f"Errore nel caricamento attività recenti: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel caricamento delle attività'
        }, status=500)

@require_http_methods(["GET"])
def api_dashboard_summary(request):
    """API per ottenere riepilogo completo della dashboard"""
    try:
        from datetime import datetime, timedelta
        from django.db.models import Count, Sum
        
        # Statistiche base
        stats = {
            'clienti_totali': Cliente.objects.count(),
            'cascine_totali': Cascina.objects.count(),
            'terreni_totali': Terreno.objects.count(),
            'superficie_totale': float(Terreno.objects.aggregate(
                totale=Sum('superficie')
            )['totale'] or 0),
            'trattamenti_programmati': Trattamento.objects.filter(stato='programmato').count(),
            'trattamenti_comunicati': Trattamento.objects.filter(stato='comunicato').count(),
            'prodotti_totali': Prodotto.objects.count(),
            'contoterzisti_totali': Contoterzista.objects.count(),
            'contatti_email_totali': ContattoEmail.objects.count(),
            'principi_attivi_totali': PrincipioAttivo.objects.count(),
        }
        
        # Attività recenti
        settimana_fa = timezone.now() - timedelta(days=7)
        attivita_settimana = ActivityLog.objects.filter(
            timestamp__gte=settimana_fa
        ).count()
        
        # Crescita rispetto alla settimana precedente
        due_settimane_fa = timezone.now() - timedelta(days=14)
        attivita_settimana_precedente = ActivityLog.objects.filter(
            timestamp__gte=due_settimane_fa,
            timestamp__lt=settimana_fa
        ).count()
        
        crescita_attivita = attivita_settimana - attivita_settimana_precedente
        
        # Top attività per tipo
        top_activities = list(ActivityLog.objects.filter(
            timestamp__gte=settimana_fa
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'activity_summary': {
                'attivita_settimana': attivita_settimana,
                'crescita': crescita_attivita,
                'top_activities': top_activities
            }
        })
        
    except Exception as e:
        logger.error(f"Errore nel caricamento riepilogo dashboard: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel caricamento del riepilogo'
        }, status=500)

@require_http_methods(["GET"])
def api_database_stats(request):
    
    """API per ottenere statistiche aggiornate del database"""

    from django.db.models import Count, Sum
    try:
        stats = {
            'clienti': Cliente.objects.count(),
            'cascine': Cascina.objects.count(),
            'terreni': Terreno.objects.count(),
            'contoterzisti': Contoterzista.objects.count(),
            'prodotti': Prodotto.objects.count(),
            'principi_attivi': PrincipioAttivo.objects.count(),
            'contatti_email': ContattoEmail.objects.count(),
            'trattamenti': Trattamento.objects.count(),
        }
        
        # Calcola superficie totale
        superficie_totale = Terreno.objects.aggregate(
            totale=Sum('superficie')
        )['totale'] or 0
        
        stats['superficie_totale'] = float(superficie_totale)
        
        # Statistiche attività
        oggi_inizio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stats['attivita_oggi'] = ActivityLog.objects.filter(
            timestamp__gte=oggi_inizio
        ).count()
        
        settimana_fa = timezone.now() - timedelta(days=7)
        stats['attivita_settimana'] = ActivityLog.objects.filter(
            timestamp__gte=settimana_fa
        ).count()
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Errore nel caricamento statistiche: {str(e)}")
        return JsonResponse({'error': 'Errore nel caricamento statistiche'}, status=500)

# ============ API MANAGEMENT ATTIVITÀ (OPZIONALI) ============

@csrf_exempt
@require_http_methods(["POST"])
def api_cleanup_activities(request):
    """API per pulire le attività vecchie (solo per admin)"""
    try:
        days_to_keep = int(request.POST.get('days', 90))
        
        from .activity_logging import cleanup_old_logs
        deleted_count = cleanup_old_logs(days_to_keep)
        
        return JsonResponse({
            'success': True,
            'message': f'Eliminati {deleted_count} log di attività',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Errore nella pulizia attività: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nella pulizia delle attività'
        }, status=500)

@require_http_methods(["GET"])
def api_activity_stats(request):
    """API per ottenere statistiche delle attività"""
    try:
        days = int(request.GET.get('days', 7))
        
        from .activity_logging import get_activity_stats
        stats = get_activity_stats(days)
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Errore nel caricamento statistiche attività: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Errore nel caricamento delle statistiche'
        }, status=500)



@require_http_methods(["GET"])
def api_clienti(request):
    """API per ottenere lista clienti con informazioni sulle cascine"""
    try:
        clienti = Cliente.objects.prefetch_related('cascine').all().order_by('nome')
        
        clienti_data = []
        for cliente in clienti:
            cascine_count = cliente.cascine.count()
            superficie_totale = sum(
                sum(terreno.superficie for terreno in cascina.terreni.all()) 
                for cascina in cliente.cascine.all()
            )
            
            clienti_data.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'cascine_count': cascine_count,
                'superficie_totale': float(superficie_totale),
                'cascine': [
                    {
                        'id': cascina.id,
                        'nome': cascina.nome,
                        'superficie_totale': float(sum(t.superficie for t in cascina.terreni.all()))
                    } for cascina in cliente.cascine.all()
                ]
            })
        
        return JsonResponse(clienti_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@require_http_methods(["GET"])
def api_cliente_cascine(request, cliente_id):
    """API per ottenere cascine di un cliente specifico"""
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        cascine = cliente.cascine.prefetch_related('terreni', 'contoterzista').all()
        
        cascine_data = []
        for cascina in cascine:
            superficie_totale = sum(terreno.superficie for terreno in cascina.terreni.all())
            terreni_count = cascina.terreni.count()
            
            cascine_data.append({
                'id': cascina.id,
                'nome': cascina.nome,
                'cliente_id': cliente.id,
                'cliente_nome': cliente.nome,
                'superficie_totale': float(superficie_totale),
                'terreni_count': terreni_count,
                'contoterzista': cascina.contoterzista.nome if cascina.contoterzista else None,
                'contoterzista_id': cascina.contoterzista.id if cascina.contoterzista else None,
                'terreni': [
                    {
                        'id': terreno.id,
                        'nome': terreno.nome,
                        'superficie': float(terreno.superficie)
                    } for terreno in cascina.terreni.all()
                ]
            })
        
        return JsonResponse(cascine_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_cascina_terreni(request, cascina_id):
    """API per ottenere terreni di una cascina specifica"""
    try:
        cascina = get_object_or_404(Cascina, id=cascina_id)
        terreni = cascina.terreni.all().order_by('nome')
        
        terreni_data = [{
            'id': terreno.id,
            'nome': terreno.nome,
            'superficie': float(terreno.superficie),
            'cascina_id': cascina.id,
            'cascina_nome': cascina.nome,
            'cliente_id': cascina.cliente.id,
            'cliente_nome': cascina.cliente.nome
        } for terreno in terreni]
        
        return JsonResponse(terreni_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_search_clienti(request):
    """API per ricerca clienti con autocompletamento"""
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse([], safe=False)
        
        clienti = Cliente.objects.filter(
            nome__icontains=query
        ).prefetch_related('cascine').order_by('nome')[:10]
        
        results = []
        for cliente in clienti:
            cascine_count = cliente.cascine.count()
            superficie_totale = sum(
                sum(terreno.superficie for terreno in cascina.terreni.all()) 
                for cascina in cliente.cascine.all()
            )
            
            results.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'cascine_count': cascine_count,
                'superficie_totale': float(superficie_totale)
            })
        
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)