# domenico/templatetags/aziende_extras.py (aggiorna il file esistente)

from django import template
from urllib.parse import urlencode

register = template.Library()

@register.filter
def total_cascine(aziende_tree):
    """Calcola il numero totale di cascine"""
    total = 0
    for cliente in aziende_tree:
        total += len(cliente['cascine'])
    return total

@register.filter
def total_terreni(aziende_tree):
    """Calcola il numero totale di terreni"""
    total = 0
    for cliente in aziende_tree:
        for cascina in cliente['cascine']:
            total += len(cascina['terreni'])
    return total

@register.filter
def total_superficie(aziende_tree):
    """Calcola la superficie totale"""
    total = 0
    for cliente in aziende_tree:
        total += float(cliente['superficie_totale'] or 0)
    return round(total, 2)

@register.filter
def split(value, delimiter):
    """Divide una stringa usando il delimitatore specificato"""
    if not value:
        return []
    return value.split(delimiter)

@register.filter
def get_livello_display(trattamento):
    """Restituisce la descrizione del livello di applicazione"""
    livello_map = {
        'cliente': 'Intera Azienda',
        'cascina': 'Cascina',
        'terreno': 'Terreni Selezionati',
    }
    return livello_map.get(trattamento.livello_applicazione, 'Non specificato')

@register.filter
def get_stato_badge_class(stato):
    """Restituisce la classe CSS per il badge dello stato"""
    stato_classes = {
        'programmato': 'status-programmato',
        'comunicato': 'status-comunicato',
        'completato': 'status-completato',
        'annullato': 'status-annullato',
    }
    return stato_classes.get(stato, 'status-programmato')

@register.filter
def get_stato_icon(stato):
    """Restituisce l'icona FontAwesome per lo stato"""
    stato_icons = {
        'programmato': 'fas fa-calendar-plus',
        'comunicato': 'fas fa-paper-plane',
        'completato': 'fas fa-check-circle',
        'annullato': 'fas fa-times-circle',
    }
    return stato_icons.get(stato, 'fas fa-circle')

@register.filter
def format_superficie(superficie):
    """Formatta la superficie con unità di misura"""
    if superficie is None:
        return "0 ha"
    return f"{superficie:.2f} ha"

@register.filter
def truncate_smart(text, length=50):
    """Tronca il testo in modo intelligente"""
    if not text or len(text) <= length:
        return text
    return text[:length-3] + "..."

@register.filter
def get_client_initials(client_name):
    """Restituisce le iniziali del nome cliente"""
    if not client_name:
        return "??"
    words = client_name.split()
    if len(words) == 1:
        return words[0][:2].upper()
    return ''.join([word[0].upper() for word in words[:2]])

@register.filter
def count_products(trattamento):
    """Conta i prodotti di un trattamento"""
    return trattamento.trattamentoprodotto_set.count()

@register.filter
def get_first_products(trattamento, limit=3):
    """Restituisce i primi N prodotti di un trattamento"""
    return trattamento.trattamentoprodotto_set.all()[:limit]

@register.filter
def has_remaining_products(trattamento, limit=3):
    """Verifica se ci sono prodotti oltre il limite"""
    return trattamento.trattamentoprodotto_set.count() > limit

@register.filter
def remaining_products_count(trattamento, limit=3):
    """Conta i prodotti rimanenti oltre il limite"""
    total = trattamento.trattamentoprodotto_set.count()
    return max(0, total - limit)

@register.simple_tag
def url_replace(request, **kwargs):
    """Sostituisce parametri URL mantenendo gli altri"""
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            query[key] = value
        elif key in query:
            del query[key]
    return query.urlencode()

@register.filter
def multiply(value, arg):
    """Moltiplica due valori"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

# NUOVI FILTRI PER LE COMUNICAZIONI

@register.filter
def format_email_list(emails_string, max_display=3):
    """Formatta una lista di email per visualizzazione"""
    if not emails_string:
        return []
    
    emails = emails_string.split(', ')
    if len(emails) <= max_display:
        return emails
    
    return emails[:max_display] + [f'+{len(emails) - max_display} altri']

@register.filter
def email_domain(email):
    """Estrae il dominio da un indirizzo email"""
    if not email or '@' not in email:
        return email
    return email.split('@')[1]

@register.filter
def success_rate(stats):
    """Calcola la percentuale di successo delle comunicazioni"""
    if not stats or stats.get('totali', 0) == 0:
        return 0
    
    riuscite = stats.get('riuscite', 0)
    totali = stats.get('totali', 1)
    
    return round((riuscite / totali) * 100, 1)

@register.filter
def failure_rate(stats):
    """Calcola la percentuale di fallimento delle comunicazioni"""
    if not stats or stats.get('totali', 0) == 0:
        return 0
    
    fallite = stats.get('fallite', 0)
    totali = stats.get('totali', 1)
    
    return round((fallite / totali) * 100, 1)

@register.filter
def get_querystring_with_view(request, view_type=None):
    """
    Genera la querystring preservando il parametro view e tutti gli altri parametri
    tranne 'page' (usato per paginazione)
    """
    params = request.GET.copy()
    
    # Rimuovi il parametro page se presente (per la paginazione)
    if 'page' in params:
        del params['page']
    
    # Aggiungi o aggiorna il parametro view se specificato
    if view_type and view_type != 'dashboard':
        params['view'] = view_type
    elif 'view' not in params and hasattr(request, 'resolver_match'):
        # Prendi il view_type dal context se disponibile
        pass
    
    # Genera la querystring
    if params:
        return '&' + urlencode(params)
    return ''

@register.filter
def preserve_filters(request, exclude_param=None):
    """
    Preserva tutti i filtri tranne quello specificato in exclude_param
    """
    params = request.GET.copy()
    
    if exclude_param and exclude_param in params:
        del params[exclude_param]
    
    if params:
        return urlencode(params) + '&'
    return ''

@register.simple_tag
def url_with_params(request, **kwargs):
    """
    Genera URL preservando i parametri esistenti e aggiungendo/modificando quelli specificati
    """
    params = request.GET.copy()
    
    # Aggiorna i parametri con quelli specificati
    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
        elif key in params:
            del params[key]
    
    if params:
        return '?' + urlencode(params)
    return '?'

@register.inclusion_tag('snippets/pagination.html')
def paginate_with_filters(page_obj, request):
    """
    Tag per renderizzare la paginazione preservando tutti i filtri
    """
    return {
        'page_obj': page_obj,
        'request': request,
        'is_paginated': page_obj.has_other_pages() if page_obj else False
    }

@register.filter
def prodotti_summary(trattamento):
    prodotti = trattamento.trattamentoprodotto_set.all()
    if not prodotti:
        return "Nessun prodotto"
    
    if prodotti.count() == 1:
        tp = prodotti.first()
        return f"{tp.prodotto.nome}: {tp.quantita_per_ettaro} {tp.prodotto.unita_misura}/ha"
    else:
        return f"{prodotti.count()} prodotti utilizzati"

@register.filter
def has_prodotti(trattamento):
    return trattamento.trattamentoprodotto_set.exists()

@register.filter
def prodotti_count(trattamento):
    return trattamento.trattamentoprodotto_set.count()



@register.filter
def total_terreni(cascine_list):
    """Calcola il numero totale di terreni da una lista di cascine"""
    total = 0
    for cascina in cascine_list:
        if hasattr(cascina, 'terreni'):
            total += len(cascina['terreni']) if isinstance(cascina, dict) else cascina.terreni.count()
        elif isinstance(cascina, dict) and 'terreni_count' in cascina:
            total += cascina['terreni_count']
    return total

@register.filter
def total_superficie(items):
    """Calcola la superficie totale da una lista di items (terreni o cascine)"""
    total = 0.0
    
    if not items:
        return 0.0
    
    # Se è una lista di terreni
    if hasattr(items, 'all'):  # QuerySet
        for item in items.all():
            if hasattr(item, 'superficie'):
                total += float(item.superficie or 0)
    elif isinstance(items, list):  # Lista normale
        for item in items:
            if isinstance(item, dict):
                total += float(item.get('superficie_totale', 0) or item.get('superficie', 0))
            elif hasattr(item, 'superficie'):
                total += float(item.superficie or 0)
            elif hasattr(item, 'superficie_totale'):
                total += float(item.superficie_totale or 0)
    
    return round(total, 2)

@register.filter
def get_contoterzista_name(cascina):
    """Ottiene il nome del contoterzista in modo sicuro"""
    if isinstance(cascina, dict):
        contoterzista = cascina.get('contoterzista')
        if isinstance(contoterzista, dict):
            return contoterzista.get('nome', 'Non assegnato')
        elif hasattr(contoterzista, 'nome'):
            return contoterzista.nome
        elif isinstance(contoterzista, str):
            return contoterzista
    elif hasattr(cascina, 'contoterzista') and cascina.contoterzista:
        return cascina.contoterzista.nome
    
    return 'Non assegnato'

@register.filter
def get_terreni_count(cascina):
    """Ottiene il numero di terreni in modo sicuro"""
    if isinstance(cascina, dict):
        return cascina.get('terreni_count', 0)
    elif hasattr(cascina, 'terreni'):
        return cascina.terreni.count()
    return 0

@register.filter 
def format_number(value, decimals=1):
    """Formatta un numero con il numero specificato di decimali"""
    try:
        return f"{float(value):.{decimals}f}"
    except (ValueError, TypeError):
        return "0"

@register.filter
def safe_get(dictionary, key):
    """Ottiene un valore da un dizionario in modo sicuro"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

@register.simple_tag
def get_breadcrumb_icon(level):
    """Restituisce l'icona appropriata per il livello del breadcrumb"""
    icons = {
        'aziende': 'fas fa-building',
        'cascine': 'fas fa-home',
        'terreni': 'fas fa-seedling'
    }
    return icons.get(level, 'fas fa-circle')

@register.inclusion_tag('components/breadcrumb_item.html')
def breadcrumb_item(url, icon, text, is_active=False):
    """Template tag per creare un elemento breadcrumb"""
    return {
        'url': url,
        'icon': icon,
        'text': text,
        'is_active': is_active
    }

@register.filter
def pluralize_it(value, singular_plural):
    """Pluralizzazione italiana personalizzata"""
    try:
        count = int(value)
        singular, plural = singular_plural.split(',')
        return singular if count == 1 else plural
    except (ValueError, AttributeError):
        return singular_plural.split(',')[0] if ',' in singular_plural else singular_plural