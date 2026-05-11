from django import template

register = template.Library()

VITAL_RANGES = {
    'bp_sys': {'low': 90, 'high': 140, 'critical_low': 70, 'critical_high': 180},
    'bp_dia': {'low': 60, 'high': 90, 'critical_low': 40, 'critical_high': 120},
    'spo2': {'low': 95, 'high': 100, 'critical_low': 90, 'critical_high': 100},
    'pulse': {'low': 60, 'high': 100, 'critical_low': 40, 'critical_high': 150},
    'rr': {'low': 12, 'high': 20, 'critical_low': 8, 'critical_high': 30},
    'temp': {'low': 36.1, 'high': 37.2, 'critical_low': 35.0, 'critical_high': 39.0},
}

@register.filter
def vital_class(value, vital_name):
    """Return a CSS class based on whether the vital sign is normal, warning, or critical."""
    if value is None or value == '':
        return ''
    try:
        val = float(value)
    except (ValueError, TypeError):
        return ''
    
    ranges = VITAL_RANGES.get(vital_name)
    if not ranges:
        return ''
    
    if val <= ranges['critical_low'] or val >= ranges['critical_high']:
        return 'text-danger fw-bold'
    elif val < ranges['low'] or val > ranges['high']:
        return 'text-warning fw-bold'
    return 'text-success'


@register.filter
def vital_icon(value, vital_name):
    """Return an icon indicator for abnormal vitals."""
    if value is None or value == '':
        return ''
    try:
        val = float(value)
    except (ValueError, TypeError):
        return ''
    
    ranges = VITAL_RANGES.get(vital_name)
    if not ranges:
        return ''
    
    if val <= ranges['critical_low'] or val >= ranges['critical_high']:
        return '<i class="bi bi-exclamation-triangle-fill text-danger ms-1" title="Critical"></i>'
    elif val < ranges['low'] or val > ranges['high']:
        return '<i class="bi bi-exclamation-circle text-warning ms-1" title="Abnormal"></i>'
    return ''

@register.filter(name='can_view_medical_data')
def can_view_medical_data(visit, user):
    """
    Template filter to check if a user can view medical data for a visit.
    Usage: {% if visit|can_view_medical_data:request.user %}
    """
    if not hasattr(visit, 'can_view_medical_data'):
        return False
    return visit.can_view_medical_data(user)

@register.filter(name='visible_visits')
def visible_visits(patient, user):
    """
    Template filter to get visible visits for a patient based on the user's permissions.
    Usage: {% for visit in patient|visible_visits:request.user %}
    """
    from medical_records.models import Visit
    if not hasattr(patient, 'visits'):
        return []
    return Visit.objects.visible_to(user).filter(patient=patient).order_by('-visit_date')

@register.filter
def get_item(dictionary, key):
    """
    Returns the value of a key in a dictionary.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if not dictionary:
        return ""
    return dictionary.get(str(key), "")

@register.filter(name='split')
def split(value, arg):
    """
    Splits a string by a delimiter.
    Usage: {{ "1,2,3"|split:"," }}
    """
    return value.split(arg)
