from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    return dictionary.get(key, [])

@register.filter
def percentage(value, max_value):
    if value is None or max_value is None or max_value == 0:
        return 0
    return int((value / max_value) * 100)

@register.filter
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False 