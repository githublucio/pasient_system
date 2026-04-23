from django import template
from laboratory.views import CBC_RANGES

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Usage: {{ my_dict|get_item:param_key }}
    """
    if not dictionary:
        return ""
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")

@register.filter
def replace(value, arg):
    """
    Usage: {{ value|replace:"old,new" }}
    """
    if not value:
        return ""
    if "," in arg:
        old, new = arg.split(",")
    else:
        old, new = arg, " "
    return value.replace(old, new)

@register.filter
def get_cbc_range(key, category):
    """
    Usage: {{ key|get_cbc_range:category }}
    """
    if not category:
        return "-"
    ranges = CBC_RANGES.get(category, {})
    return ranges.get(key, "-")
