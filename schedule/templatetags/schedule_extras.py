from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return value - arg
    except (ValueError, TypeError):
        try:
            return value - len(arg)
        except (ValueError, TypeError):
            return 0

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key."""
    return dictionary.get(key, None)