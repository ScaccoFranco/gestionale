# domenico/activity_logging.py
# Crea questo file per gestire il logging delle attività

from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def log_activity(activity_type, title, description='', related_object=None, 
                 request=None, extra_data=None):
    """
    Funzione helper per registrare un'attività
    
    Args:
        activity_type (str): Tipo di attività (deve essere in ACTIVITY_TYPES)
        title (str): Titolo dell'attività
        description (str): Descrizione opzionale
        related_object: Oggetto Django correlato (Cliente, Terreno, etc.)
        request: Oggetto request Django per IP e user agent
        extra_data (dict): Dati aggiuntivi da salvare
    """
    try:
        from .models import ActivityLog
        
        # Prepara dati dell'oggetto correlato
        related_object_type = None
        related_object_id = None
        related_object_name = None
        
        if related_object:
            related_object_type = related_object.__class__.__name__
            related_object_id = related_object.pk
            related_object_name = str(related_object)
        
        # Prepara dati dalla request
        ip_address = None
        user_agent = ''
        
        if request:
            # Ottieni IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            # Ottieni user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Crea il log
        ActivityLog.objects.create(
            activity_type=activity_type,
            title=title,
            description=description,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            related_object_name=related_object_name,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data or {}
        )
        
        logger.info(f"✅ Attività registrata: {title}")
        
    except Exception as e:
        logger.error(f"❌ Errore nel logging attività: {str(e)}")

# Funzioni specifiche per ogni tipo di attività

def log_cliente_created(cliente, request=None):
    """Log per creazione cliente"""
    log_activity(
        activity_type='cliente_created',
        title=f'Nuovo cliente: {cliente.nome}',
        description=f'È stato aggiunto il cliente {cliente.nome} al database',
        related_object=cliente,
        request=request,
        extra_data={
            'cliente_id': cliente.id,
            'cliente_nome': cliente.nome,
        }
    )

def log_terreno_created(terreno, request=None):
    """Log per creazione terreno"""
    log_activity(
        activity_type='terreno_created',
        title=f'Nuovo terreno: {terreno.nome}',
        description=f'È stato aggiunto il terreno {terreno.nome} ({terreno.superficie} ha) alla cascina {terreno.cascina.nome}',
        related_object=terreno,
        request=request,
        extra_data={
            'terreno_id': terreno.id,
            'terreno_nome': terreno.nome,
            'superficie': float(terreno.superficie),
            'cascina_id': terreno.cascina.id,
            'cascina_nome': terreno.cascina.nome,
            'cliente_nome': terreno.cascina.cliente.nome
        }
    )

def log_prodotto_created(prodotto, principi_attivi=None, request=None):
    """Log per creazione prodotto"""
    principi_list = []
    if principi_attivi:
        principi_list = [pa.nome for pa in principi_attivi]
    
    log_activity(
        activity_type='prodotto_created',
        title=f'Nuovo prodotto: {prodotto.nome}',
        description=f'È stato aggiunto il prodotto {prodotto.nome} ({prodotto.unita_misura}) con principi attivi: {", ".join(principi_list)}',
        related_object=prodotto,
        request=request,
        extra_data={
            'prodotto_id': prodotto.id,
            'prodotto_nome': prodotto.nome,
            'unita_misura': prodotto.unita_misura,
            'principi_attivi': principi_list,
            'descrizione': prodotto.descrizione
        }
    )

def log_contoterzista_created(contoterzista, request=None):
    """Log per creazione contoterzista"""
    log_activity(
        activity_type='contoterzista_created',
        title=f'Nuovo contoterzista: {contoterzista.nome}',
        description=f'È stato aggiunto il contoterzista {contoterzista.nome}',
        related_object=contoterzista,
        request=request,
        extra_data={
            'contoterzista_id': contoterzista.id,
            'contoterzista_nome': contoterzista.nome,
            'telefono': contoterzista.telefono,
            'email': contoterzista.email
        }
    )

def log_contatto_created(contatto, request=None):
    """Log per creazione contatto email"""
    log_activity(
        activity_type='contatto_created',
        title=f'Nuovo contatto: {contatto.nome}',
        description=f'È stato aggiunto il contatto email {contatto.nome} ({contatto.email}) per {contatto.cliente.nome}',
        related_object=contatto,
        request=request,
        extra_data={
            'contatto_id': contatto.id,
            'contatto_nome': contatto.nome,
            'contatto_email': contatto.email,
            'cliente_id': contatto.cliente.id,
            'cliente_nome': contatto.cliente.nome,
            'ruolo': contatto.ruolo,
            'priorita': contatto.priorita
        }
    )

def log_trattamento_created(trattamento, request=None):
    """Log per creazione trattamento"""
    superficie = trattamento.get_superficie_interessata()
    
    log_activity(
        activity_type='trattamento_created',
        title=f'Nuovo trattamento per {trattamento.cliente.nome}',
        description=f'È stato programmato un trattamento per {trattamento.cliente.nome} su {superficie} ettari',
        related_object=trattamento,
        request=request,
        extra_data={
            'trattamento_id': trattamento.id,
            'cliente_nome': trattamento.cliente.nome,
            'superficie_interessata': float(superficie),
            'livello_applicazione': trattamento.livello_applicazione,
            'stato': trattamento.stato,
        }
    )

def log_comunicazione_sent(trattamento, destinatari_count, request=None):
    """Log per invio comunicazione"""
    log_activity(
        activity_type='comunicazione_sent',
        title=f'Comunicazione inviata per trattamento #{trattamento.id}',
        description=f'È stata inviata la comunicazione per il trattamento di {trattamento.cliente.nome} a {destinatari_count} destinatari',
        related_object=trattamento,
        request=request,
        extra_data={
            'trattamento_id': trattamento.id,
            'cliente_nome': trattamento.cliente.nome,
            'destinatari_count': destinatari_count,
            'data_comunicazione': timezone.now().isoformat()
        }
    )

def log_cascina_created(cascina, request=None):
    """Log per creazione cascina"""
    contoterzista_info = f' con contoterzista {cascina.contoterzista.nome}' if cascina.contoterzista else ''
    
    log_activity(
        activity_type='cascina_created',
        title=f'Nuova cascina: {cascina.nome}',
        description=f'È stata aggiunta la cascina {cascina.nome} per il cliente {cascina.cliente.nome}{contoterzista_info}',
        related_object=cascina,
        request=request,
        extra_data={
            'cascina_id': cascina.id,
            'cascina_nome': cascina.nome,
            'cliente_id': cascina.cliente.id,
            'cliente_nome': cascina.cliente.nome,
            'contoterzista_id': cascina.contoterzista.id if cascina.contoterzista else None,
            'contoterzista_nome': cascina.contoterzista.nome if cascina.contoterzista else None
        }
    )