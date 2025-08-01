from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
import json
import io
from decimal import Decimal
from .models import *

@csrf_exempt
@require_http_methods(["POST"])
def api_communication_preview(request):
    """
    API per ottenere l'anteprima dei dati dei trattamenti da comunicare
    raggruppati per azienda
    """
    try:
        data = json.loads(request.body)
        trattamenti_ids = data.get('trattamenti_ids', [])
        
        if not trattamenti_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nessun trattamento specificato'
            }, status=400)
        
        # Recupera i trattamenti con tutte le relazioni necessarie
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
                'error': 'Nessun trattamento trovato con gli ID specificati'
            }, status=404)
        
        # Raggruppa per cliente e prepara i dati
        preview_data = []
        clienti_map = {}
        
        for trattamento in trattamenti:
            cliente_nome = trattamento.cliente.nome
            
            # Calcola superficie interessata
            superficie = trattamento.get_superficie_interessata()
            
            # Prepara dati prodotti
            prodotti_data = []
            for tp in trattamento.trattamentoprodotto_set.all():
                prodotti_data.append({
                    'nome': tp.prodotto.nome,
                    'quantita_per_ettaro': float(tp.get_quantita_per_ettaro()),
                    'unita_misura': tp.prodotto.unita_misura,
                    'quantita_totale': float(tp.tp.get_quantita_per_ettaro() * Decimal(str(superficie)))
                })
            
            # Prepara dati terreni (se applicabile)
            terreni_data = []
            if trattamento.livello_applicazione == 'terreno':
                for terreno in trattamento.terreni.all():
                    terreni_data.append({
                        'nome': terreno.nome,
                        'superficie': float(terreno.superficie)
                    })
            
            trattamento_data = {
                'id': trattamento.id,
                'livello_applicazione': trattamento.livello_applicazione,
                'superficie_interessata': float(superficie),
                'data_esecuzione_prevista': trattamento.data_esecuzione_prevista.strftime('%d/%m/%Y') if trattamento.data_esecuzione_prevista else None,
                'note': trattamento.note,
                'prodotti': prodotti_data,
                'terreni': terreni_data,
                'cascina_nome': trattamento.cascina.nome if trattamento.cascina else None
            }
            
            if cliente_nome not in clienti_map:
                clienti_map[cliente_nome] = {
                    'cliente_nome': cliente_nome,
                    'trattamenti': [],
                    'superficie_totale': 0
                }
            
            clienti_map[cliente_nome]['trattamenti'].append(trattamento_data)
            clienti_map[cliente_nome]['superficie_totale'] += float(superficie)
        
        # Converte in lista per la risposta
        email_previews = list(clienti_map.values())
        
        return JsonResponse({
            'success': True,
            'email_previews': email_previews,
            'trattamenti_count': len(trattamenti),
            'clienti_count': len(clienti_map)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON non valido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la preparazione anteprima: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_generate_company_pdf(request):
    """
    API per generare un PDF di comunicazione per una specifica azienda
    con tutti i suoi trattamenti e note personalizzate
    """
    try:
        data = json.loads(request.body)
        trattamenti_ids = data.get('trattamenti_ids', [])
        company_name = data.get('company_name', '')
        custom_notes = data.get('custom_notes', '')
        update_status = data.get('update_status', True)
        
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
        pdf_content = generate_company_communication_pdf(
            trattamenti, 
            custom_notes
        )
        
        # Aggiorna lo stato dei trattamenti se richiesto
        if update_status:
            with transaction.atomic():
                for trattamento in trattamenti:
                    if trattamento.stato == 'programmato':
                        trattamento.stato = 'comunicato'
                        trattamento.data_comunicazione = timezone.now()
                        trattamento.save()
        
        # Prepara la risposta HTTP con il PDF
        filename = f"Comunicazione_{company_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON non valido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Errore durante la generazione del PDF: {str(e)}'
        }, status=500)


def generate_company_communication_pdf(trattamenti, custom_notes=''):
    """
    Genera un PDF di comunicazione per un'azienda con tutti i suoi trattamenti
    """
    try:
        # Import per PDF (prova prima WeasyPrint, poi xhtml2pdf)
        try:
            from weasyprint import HTML, CSS
            pdf_engine = 'weasyprint'
        except ImportError:
            try:
                from xhtml2pdf import pisa
                pdf_engine = 'xhtml2pdf'
            except ImportError:
                raise Exception("Nessun motore PDF disponibile. Installa WeasyPrint o xhtml2pdf.")
        
        # Prepara i dati per il template
        cliente = trattamenti.first().cliente
        
        # Calcola totali
        superficie_totale = sum(t.get_superficie_interessata() for t in trattamenti)
        
        # Raggruppa prodotti per calcolare totali
        prodotti_totali = {}
        for trattamento in trattamenti:
            for tp in trattamento.trattamentoprodotto_set.all():
                prodotto_nome = tp.prodotto.nome
                if prodotto_nome not in prodotti_totali:
                    prodotti_totali[prodotto_nome] = {
                        'nome': prodotto_nome,
                        'unita_misura': tp.prodotto.unita_misura,
                        'quantita_totale': Decimal('0')
                    }
                
                quantita_trattamento = tp.get_quantita_per_ettaro() * Decimal(str(trattamento.get_superficie_interessata()))
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
        
        # Renderizza il template HTML
        html_content = render_to_string('pdf/comunicazione_trattamenti.html', context)
        
        # Genera PDF in base al motore disponibile
        if pdf_engine == 'weasyprint':
            # CSS per il PDF
            css_content = """
                @page {
                    size: A4;
                    margin: 2cm;
                }
                body {
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.4;
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #0d6efd;
                    padding-bottom: 20px;
                }
                .company-info {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                .treatment-item {
                    border: 1px solid #dee2e6;
                    margin-bottom: 15px;
                    padding: 15px;
                    page-break-inside: avoid;
                }
                .product-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }
                .product-table th,
                .product-table td {
                    border: 1px solid #dee2e6;
                    padding: 8px;
                    text-align: left;
                }
                .product-table th {
                    background: #f8f9fa;
                    font-weight: bold;
                }
                .summary-section {
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .custom-notes {
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    font-size: 10pt;
                    color: #6c757d;
                }
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
        
        return pdf_content
        
    except Exception as e:
        raise Exception(f"Errore nella generazione del PDF: {str(e)}")


# Modifica la funzione executeBulkAction esistente per reindirizzare al wizard
def redirect_to_communication_wizard(selected_treatments):
    """
    Invece di eseguire direttamente la comunicazione, reindirizza al wizard
    """
    # Questa funzione viene chiamata dal JavaScript modificato
    treatment_ids = ','.join(map(str, selected_treatments))
    redirect_url = f'/comunicazione-wizard/?treatments={treatment_ids}'
    return redirect_url