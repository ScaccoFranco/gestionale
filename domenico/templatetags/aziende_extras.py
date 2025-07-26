
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