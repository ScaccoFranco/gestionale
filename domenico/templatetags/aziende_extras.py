from django import template

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

# NUOVE FUNZIONI PER I TRATTAMENTI

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
        'in_esecuzione': 'status-in_esecuzione',
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
        'in_esecuzione': 'fas fa-cogs',
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