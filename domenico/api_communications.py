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
        from weasyprint import HTML, CSS
        pdf_engine = 'weasyprint'
    except ImportError:
        try:
            from xhtml2pdf import pisa
            pdf_engine = 'xhtml2pdf'
        except ImportError:
            raise Exception("Nessun motore PDF disponibile. Installa WeasyPrint o xhtml2pdf.")
    
    if not trattamenti:
        raise Exception("Nessun trattamento fornito per la generazione del PDF")
    
    # Prendi i dati dell'azienda dal primo trattamento
    primo_trattamento = trattamenti[0]
    azienda = primo_trattamento.terreno.cascina.cliente
    
    # Raggruppa i trattamenti per terreno
    trattamenti_per_terreno = {}
    for trattamento in trattamenti:
        terreno_key = f"{trattamento.terreno.cascina.nome} - {trattamento.terreno.nome}"
        if terreno_key not in trattamenti_per_terreno:
            trattamenti_per_terreno[terreno_key] = {
                'terreno': trattamento.terreno,
                'trattamenti': []
            }
        trattamenti_per_terreno[terreno_key]['trattamenti'].append(trattamento)
    
    # Template HTML per il PDF (MODIFICATO)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Comunicazione Trattamenti - {azienda.nome}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                line-height: 1.4;
                margin: 20px;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .company-info {{
                margin-bottom: 30px;
                padding: 15px;
                border: 1px solid #ddd;
                background-color: #f9f9f9;
            }}
            .custom-notes {{
                margin-bottom: 30px;
                padding: 15px;
                border: 1px solid #007bff;
                background-color: #e7f3ff;
                border-radius: 5px;
            }}
            .treatments-section {{
                margin-bottom: 20px;
            }}
            .terreno-header {{
                background-color: #007bff;
                color: white;
                padding: 10px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .treatment-item {{
                border: 1px solid #ddd;
                margin-bottom: 10px;
                padding: 15px;
                background-color: #fff;
            }}
            .treatment-header {{
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
                color: #007bff;
            }}
            .treatment-details {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 10px;
            }}
            .products-list {{
                margin-top: 10px;
                padding: 10px;
                background-color: #f8f9fa;
                border-left: 4px solid #007bff;
            }}
            .product-item {{
                margin-bottom: 5px;
                padding: 5px 0;
                border-bottom: 1px dotted #ccc;
            }}
            .footer {{
                margin-top: 40px;
                font-size: 10px;
                color: #666;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>COMUNICAZIONE TRATTAMENTI FITOSANITARI</h1>
            <h2>{azienda.nome}</h2>
            <p>Data comunicazione: {timezone.now().strftime('%d/%m/%Y')}</p>
        </div>
        
        <div class="company-info">
            <h3>Dati Azienda</h3>
            <p><strong>Ragione Sociale:</strong> {azienda.nome}</p>
            <p><strong>Codice Fiscale:</strong> {azienda.codice_fiscale}</p>
            <p><strong>Indirizzo:</strong> {azienda.indirizzo}</p>
            <p><strong>Email:</strong> {azienda.email or 'N/D'}</p>
            <p><strong>Telefono:</strong> {azienda.telefono or 'N/D'}</p>
        </div>
        
        {f'''
        <div class="custom-notes">
            <h3>Note Aggiuntive</h3>
            <p>{custom_notes}</p>
        </div>
        ''' if custom_notes else ''}
        
        <div class="treatments-section">
            <h2>TRATTAMENTI COMUNICATI</h2>
    """
    
    # MODIFICA PRINCIPALE: Numerazione progressiva indipendente
    trattamento_numero = 1  # Inizia da 1 per ogni comunicazione
    
    for terreno_key, terreno_data in trattamenti_per_terreno.items():
        terreno = terreno_data['terreno']
        html_template += f"""
            <div class="terreno-header">
                {terreno.cascina.nome} - {terreno.nome} 
                (Superficie: {terreno.superficie} ha)
            </div>
        """
        
        for trattamento in terreno_data['trattamenti']:
            # RIMOZIONE: Non includiamo più le note del singolo trattamento
            html_template += f"""
                <div class="treatment-item">
                    <div class="treatment-header">
                        Trattamento N. {trattamento_numero}
                    </div>
                    <div class="treatment-details">
                        <div><strong>Data esecuzione:</strong> {trattamento.data_esecuzione.strftime('%d/%m/%Y') if trattamento.data_esecuzione else 'N/D'}</div>
                        <div><strong>Tipo intervento:</strong> {trattamento.tipo_intervento}</div>
                        <div><strong>Superficie trattata:</strong> {trattamento.superficie_trattata} ha</div>
                        <div><strong>Volume miscela:</strong> {trattamento.volume_miscela or 'N/D'} L/ha</div>
                        <div><strong>Condizioni meteo:</strong> {trattamento.condizioni_meteo or 'N/D'}</div>
                        <div><strong>Velocità vento:</strong> {trattamento.velocita_vento or 'N/D'} km/h</div>
                    </div>
            """
            
            # Aggiungi prodotti utilizzati
            if hasattr(trattamento, 'prodotti') and trattamento.prodotti.exists():
                html_template += """
                    <div class="products-list">
                        <strong>Prodotti utilizzati:</strong>
                """
                for prodotto_trattamento in trattamento.prodotti.all():
                    html_template += f"""
                        <div class="product-item">
                            <strong>{prodotto_trattamento.prodotto.nome_commerciale}</strong><br>
                            Principio attivo: {prodotto_trattamento.prodotto.principio_attivo}<br>
                            Dose: {prodotto_trattamento.dose_per_ettaro} {prodotto_trattamento.unita_misura}/ha
                        </div>
                    """
                html_template += "</div>"
            
            html_template += "</div>"
            trattamento_numero += 1  # Incrementa il numero progressivo
    
    # RIMOZIONE: Eliminiamo la sezione firme
    html_template += f"""
        </div>
        
        <div class="footer">
            <p>Documento generato automaticamente il {timezone.now().strftime('%d/%m/%Y alle %H:%M')}</p>
            <p>Sistema di Gestione Trattamenti Fitosanitari - {azienda.nome}</p>
        </div>
    </body>
    </html>
    """
    
    # Genera il PDF usando WeasyPrint o xhtml2pdf
    if pdf_engine == 'weasyprint':
        html = HTML(string=html_template)
        pdf_content = html.write_pdf()
    else:  # xhtml2pdf
        from io import BytesIO
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html_template.encode("UTF-8")), result)
        if pdf.err:
            raise Exception("Errore durante la generazione del PDF")
        pdf_content = result.getvalue()
    
    return pdf_content
# Modifica la funzione executeBulkAction esistente per reindirizzare al wizard
def redirect_to_communication_wizard(selected_treatments):
    """
    Invece di eseguire direttamente la comunicazione, reindirizza al wizard
    """
    # Questa funzione viene chiamata dal JavaScript modificato
    treatment_ids = ','.join(map(str, selected_treatments))
    redirect_url = f'/comunicazione-wizard/?treatments={treatment_ids}'
    return redirect_url