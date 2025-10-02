# domenico/email_utils.py - Versione con WeasyPrint

import os
import io
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string, get_template
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

# Configura logging
logger = logging.getLogger('domenico.email_utils')

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
    PDF_ENGINE="weasyprint"
    print("✅ WeasyPrint loaded successfully")

except ImportError as e:
    print(f"⚠️  WeasyPrint not available: {e}")
    WEASYPRINT_AVAILABLE = False
    PDF_ENGINE = "None"
    
    # Classi dummy per evitare errori
    class HTML:
        def __init__(self, *args, **kwargs):
            pass
        def write_pdf(self, target):
            raise NotImplementedError("PDF generation not available - install WeasyPrint dependencies")
    
    class CSS:
        def __init__(self, *args, **kwargs):
            pass

def generate_pdf_comunicazione(trattamento_id):
    """Genera un PDF per la comunicazione del trattamento"""
    
    if not WEASYPRINT_AVAILABLE:
        raise NotImplementedError("PDF generation not available")
    
    try:
        from .models import Trattamento
        
        trattamento = Trattamento.objects.select_related(
            'cliente', 'cascina', 'cascina__contoterzista'
        ).prefetch_related(
            'terreni', 'trattamentoprodotto_set__prodotto__principi_attivi'
        ).get(id=trattamento_id)
        
        # Prepara il context per il template
        context = {
            'trattamento': trattamento,
            'now': timezone.now(),
        }
        
        # Renderizza il template HTML
        template = get_template('comunicazione_trattamento.html')
        html = template.render(context)
        
            # Usa WeasyPrint (più moderno e affidabile)
        logger.info(f"Generazione PDF con WeasyPrint per trattamento {trattamento_id}")
            
            # Crea la configurazione font
        font_config = FontConfiguration()
            
            # CSS aggiuntivo per WeasyPrint
        css = CSS(string='''
                @page {
                    margin: 2cm;
                    size: A4;
                }
                body {
                    font-family: Arial, sans-serif;
                }
            ''', font_config=font_config)
            
            # Genera il PDF
        html_doc = HTML(string=html)
        pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)
        
        logger.info(f"PDF generato con successo con WeasyPrint per trattamento {trattamento_id}")
        return pdf_bytes
            
    except Exception as e:
        logger.error(f"Errore nella generazione del PDF per trattamento {trattamento_id}: {str(e)}")
        raise Exception(f"Errore nella generazione del PDF: {str(e)}")

# Il resto delle funzioni rimane identico...
def send_trattamento_communication(trattamento_id, force_send=False):
    """
    Invia la comunicazione email per un trattamento
    
    Args:
        trattamento_id: ID del trattamento
        force_send: Se True, invia anche se già comunicato
    
    Returns:
        dict con risultato dell'invio
    """
    try:
        from .models import Trattamento, ComunicazioneTrattamento
        
        trattamento = Trattamento.objects.select_related(
            'cliente'
        ).prefetch_related(
            'cliente__contatti_email'
        ).get(id=trattamento_id)
        
        logger.info(f"Iniziando comunicazione per trattamento {trattamento_id}")
        
        # Verifica se il trattamento può essere comunicato
        if trattamento.stato not in ['programmato', 'comunicato'] and not force_send:
            return {
                'success': False,
                'error': f'Il trattamento è in stato "{trattamento.get_stato_display()}" e non può essere comunicato'
            }
        
        # Ottieni i contatti email attivi per questo cliente
        contatti_attivi = trattamento.cliente.contatti_email.filter(attivo=True).order_by('priorita', 'nome')
        
        if not contatti_attivi.exists():
            return {
                'success': False,
                'error': 'Nessun contatto email attivo trovato per questo cliente'
            }
        
        # Prepara la lista dei destinatari
        destinatari = []
        destinatari_info = []
        
        for contatto in contatti_attivi:
            destinatari.append(contatto.email)
            destinatari_info.append({
                'nome': contatto.nome,
                'email': contatto.email,
                'ruolo': contatto.ruolo
            })
        
        logger.info(f"Invio a {len(destinatari)} destinatari: {', '.join(destinatari)}")
        
        # Genera il PDF
        try:
            pdf_content = generate_pdf_comunicazione(trattamento_id)
        except Exception as e:
            logger.error(f"Errore generazione PDF: {str(e)}")
            return {
                'success': False,
                'error': f'Errore nella generazione del PDF: {str(e)}'
            }
        
        # Prepara l'oggetto dell'email
        oggetto = f"Trattamento #{trattamento.id} - {trattamento.cliente.nome}"
        if trattamento.data_esecuzione_prevista:
            oggetto += f" - Esecuzione prevista: {trattamento.data_esecuzione_prevista.strftime('%d/%m/%Y')}"
        
        # Prepara il corpo dell'email
        corpo_email = generate_email_body(trattamento)
        
        # Crea l'email
        try:
            email = EmailMultiAlternatives(
                subject=oggetto,
                body=corpo_email,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@gestionale.com'),
                to=destinatari
            )
            
            # Allega il PDF
            filename = f"Trattamento_{trattamento.id}_{trattamento.cliente.nome.replace(' ', '_')}.pdf"
            email.attach(filename, pdf_content, 'application/pdf')
            
            # Invia l'email
            email.send()
            invio_riuscito = True
            errore_invio = ""
            logger.info(f"Email inviata con successo per trattamento {trattamento_id}")
            
        except Exception as e:
            invio_riuscito = False
            errore_invio = str(e)
            logger.error(f"Errore invio email per trattamento {trattamento_id}: {str(e)}")
        
        # Registra la comunicazione nel database
        comunicazione = ComunicazioneTrattamento.objects.create(
            trattamento=trattamento,
            destinatari=', '.join(destinatari),
            oggetto=oggetto,
            corpo_email=corpo_email,
            allegati=filename,
            inviato_con_successo=invio_riuscito,
            errore=errore_invio
        )
        
        # Aggiorna lo stato del trattamento se l'invio è riuscito
        if invio_riuscito and trattamento.stato == 'programmato':
            trattamento.stato = 'comunicato'
            trattamento.save()
            logger.info(f"Stato trattamento {trattamento_id} aggiornato a 'comunicato'")
        
        return {
            'success': invio_riuscito,
            'comunicazione_id': comunicazione.id,
            'destinatari': destinatari_info,
            'destinatari_count': len(destinatari),
            'error': errore_invio if not invio_riuscito else None,
            'pdf_engine': PDF_ENGINE
        }
        
    except Exception as e:
        logger.error(f"Errore generale nella comunicazione per trattamento {trattamento_id}: {str(e)}")
        return {
            'success': False,
            'error': f'Errore durante l\'invio: {str(e)}'
        }

def generate_email_body(trattamento):
    """Genera il corpo dell'email per la comunicazione"""
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
    
    if trattamento.livello_applicazione == 'cascina' and trattamento.cascina:
        corpo_email += f"• Cascina: {trattamento.cascina.nome}\n"
    elif trattamento.livello_applicazione == 'terreno':
        terreni_nomi = [t.nome for t in trattamento.terreni.all()]
        corpo_email += f"• Terreni: {', '.join(terreni_nomi)}\n"
    
    corpo_email += f"• Prodotti: {trattamento.trattamentoprodotto_set.count()} prodotti specificati\n\n"
    
    # Aggiungi dettagli prodotti nel corpo email
    corpo_email += "PRODOTTI E QUANTITÀ:\n"
    for tp in trattamento.trattamentoprodotto_set.all():
        corpo_email += f"• {tp.prodotto.nome}: {tp.quantita_per_ettaro} {tp.prodotto.unita_misura}/ha "
        corpo_email += f"(Totale: {tp.quantita_totale:.3f} {tp.prodotto.unita_misura})\n"
    
    corpo_email += "\n"
    
    if trattamento.note:
        corpo_email += f"""
NOTE SPECIALI:
{trattamento.note}

"""
    
    corpo_email += f"""
Generato con: {PDF_ENGINE.upper() if PDF_ENGINE else 'Sistema Standard'}

Si prega di confermare la ricezione e di comunicare l'avvenuta esecuzione del trattamento.

Per qualsiasi chiarimento, non esitate a contattarci.

Cordiali saluti,
Domenico Franco
Sistema di Gestione Trattamenti Agricoli
"""
    
    return corpo_email

# Resto delle funzioni identiche ma con logging aggiornato
def preview_comunicazione_pdf(request, trattamento_id):
    """View per visualizzare l'anteprima del PDF di comunicazione"""
    try:
        pdf_content = generate_pdf_comunicazione(trattamento_id)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="preview_trattamento_{trattamento_id}.pdf"'
        
        return response
        
    except Exception as e:
        logger.error(f"Errore anteprima PDF per trattamento {trattamento_id}: {str(e)}")
        return HttpResponse(f"Errore nella generazione dell'anteprima: {str(e)}", status=500)

def download_comunicazione_pdf(request, trattamento_id):
    """View per scaricare il PDF di comunicazione"""
    try:
        from .models import Trattamento
        
        trattamento = Trattamento.objects.get(id=trattamento_id)
        pdf_content = generate_pdf_comunicazione(trattamento_id)
        
        filename = f"Trattamento_{trattamento.id}_{trattamento.cliente.nome.replace(' ', '_')}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Errore download PDF per trattamento {trattamento_id}: {str(e)}")
        return HttpResponse(f"Errore nel download: {str(e)}", status=500)

# Resto delle funzioni di utilità rimane identico...
def get_contatti_by_cliente(cliente_id):
    """Ottiene tutti i contatti email attivi per un cliente"""
    try:
        from .models import Cliente
        
        cliente = Cliente.objects.get(id=cliente_id)
        return cliente.contatti_email.filter(attivo=True).order_by('priorita', 'nome')
    except Exception as e:
        logger.error(f"Errore recupero contatti per cliente {cliente_id}: {str(e)}")
        return None

def add_contatto_email(cliente_id, nome, email, ruolo="", telefono="", priorita=1, note=""):
    """Aggiunge un nuovo contatto email per un cliente"""
    try:
        from .models import Cliente, ContattoEmail
        
        cliente = Cliente.objects.get(id=cliente_id)
        
        # Verifica se l'email esiste già per questo cliente
        if ContattoEmail.objects.filter(cliente=cliente, email=email).exists():
            return {
                'success': False,
                'error': f'Un contatto con email {email} esiste già per questo cliente'
            }
        
        contatto = ContattoEmail.objects.create(
            cliente=cliente,
            nome=nome,
            email=email,
            ruolo=ruolo,
            telefono=telefono,
            priorita=priorita,
            note=note,
            attivo=True
        )
        
        logger.info(f"Contatto {nome} ({email}) aggiunto per cliente {cliente.nome}")
        
        return {
            'success': True,
            'contatto_id': contatto.id,
            'message': f'Contatto {nome} aggiunto con successo'
        }
        
    except Exception as e:
        logger.error(f"Errore aggiunta contatto per cliente {cliente_id}: {str(e)}")
        return {
            'success': False,
            'error': f'Errore nell\'aggiunta del contatto: {str(e)}'
        }

def update_contatto_email(contatto_id, **kwargs):
    """Aggiorna un contatto email esistente"""
    try:
        from .models import ContattoEmail
        
        contatto = ContattoEmail.objects.get(id=contatto_id)
        
        # Campi aggiornabili
        campi_aggiornabili = ['nome', 'email', 'ruolo', 'telefono', 'priorita', 'attivo', 'note']
        
        for campo in campi_aggiornabili:
            if campo in kwargs:
                setattr(contatto, campo, kwargs[campo])
        
        contatto.save()
        
        logger.info(f"Contatto {contatto.nome} aggiornato")
        
        return {
            'success': True,
            'message': f'Contatto {contatto.nome} aggiornato con successo'
        }
        
    except Exception as e:
        logger.error(f"Errore aggiornamento contatto {contatto_id}: {str(e)}")
        return {
            'success': False,
            'error': f'Errore nell\'aggiornamento del contatto: {str(e)}'
        }

def delete_contatto_email(contatto_id):
    """Elimina un contatto email"""
    try:
        from .models import ContattoEmail
        
        contatto = ContattoEmail.objects.get(id=contatto_id)
        nome_contatto = contatto.nome
        cliente_nome = contatto.cliente.nome
        
        contatto.delete()
        
        logger.info(f"Contatto {nome_contatto} eliminato da cliente {cliente_nome}")
        
        return {
            'success': True,
            'message': f'Contatto {nome_contatto} eliminato con successo'
        }
        
    except Exception as e:
        logger.error(f"Errore eliminazione contatto {contatto_id}: {str(e)}")
        return {
            'success': False,
            'error': f'Errore nell\'eliminazione del contatto: {str(e)}'
        }

def test_email_configuration():
    """Testa la configurazione email"""
    try:
        from django.core.mail import send_mail
        
        # Email di test
        test_subject = 'Test Configurazione Email - Sistema Trattamenti'
        test_message = f'''
Questo è un messaggio di test per verificare la configurazione email del sistema di gestione trattamenti.

Se ricevi questo messaggio, la configurazione email funziona correttamente.

Motore PDF utilizzato: {PDF_ENGINE.upper() if PDF_ENGINE else 'Non disponibile'}
Timestamp: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}
Sistema: Gestionale Agricolo Domenico Franco
        '''
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@gestionale.com')
        to_email = getattr(settings, 'EMAIL_HOST_USER', from_email)
        
        send_mail(
            test_subject,
            test_message,
            from_email,
            [to_email],
            fail_silently=False,
        )
        
        logger.info("Email di test inviata con successo")
        
        return {
            'success': True,
            'message': f'Test email inviato con successo a {to_email}\nMotore PDF: {PDF_ENGINE or "Non disponibile"}'
        }
        
    except Exception as e:
        logger.error(f"Errore nel test email: {str(e)}")
        return {
            'success': False,
            'error': f'Errore nel test email: {str(e)}'
        }

def get_comunicazioni_stats():
    """Ottiene statistiche sulle comunicazioni inviate"""
    try:
        from .models import ComunicazioneTrattamento
        from django.db.models import Count
        
        oggi = timezone.now().date()
        
        stats = {
            'totali': ComunicazioneTrattamento.objects.count(),
            'riuscite': ComunicazioneTrattamento.objects.filter(inviato_con_successo=True).count(),
            'fallite': ComunicazioneTrattamento.objects.filter(inviato_con_successo=False).count(),
            'oggi': ComunicazioneTrattamento.objects.filter(data_invio__date=oggi).count(),
            'questa_settimana': ComunicazioneTrattamento.objects.filter(
                data_invio__date__gte=oggi - timezone.timedelta(days=7)
            ).count(),
            'questo_mese': ComunicazioneTrattamento.objects.filter(
                data_invio__year=oggi.year,
                data_invio__month=oggi.month
            ).count()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Errore nel calcolo statistiche comunicazioni: {str(e)}")
        return {}

def debug_email_settings():
    """Mostra le impostazioni email attuali (per debug)"""
    email_settings = {
        'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'Non configurato'),
        'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'Non configurato'),
        'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'Non configurato'),
        'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', 'Non configurato'),
        'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Non configurato'),
        'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'Non configurato')[:10] + '...' if getattr(settings, 'EMAIL_HOST_USER', '') else 'Non configurato',
        'PDF_ENGINE': PDF_ENGINE or 'Non disponibile',
        'PDF_AVAILABLE': PDF_AVAILABLE
    }
    
    return email_settings