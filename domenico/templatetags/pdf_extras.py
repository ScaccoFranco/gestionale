from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def mul(value, multiplier):
    """Moltiplica due valori"""
    try:
        return Decimal(str(value)) * Decimal(str(multiplier))
    except:
        return 0

@register.filter
def pluralize_it(value, forms):
    """Pluralizzazione italiana personalizzata"""
    try:
        value = int(value)
        singular, plural = forms.split(',')
        return singular if value == 1 else plural
    except:
        return forms