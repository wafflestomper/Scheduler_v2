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

@register.filter
def add_class(field, css_class):
    """Add a CSS class to a Django form field."""
    return field.as_widget(attrs={"class": css_class})

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) - float(arg)
        except (ValueError, TypeError):
            return 0 