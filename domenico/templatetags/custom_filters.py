from django import template

register = template.Library()

@register.filter
def split(value, key):
    """Divide una stringa in una lista usando il separatore `key`."""
    if not value:
        return []
    return value.split(key)
