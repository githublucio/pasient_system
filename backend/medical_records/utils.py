from django.utils import timezone
from .models import VisitLog


def log_visit_action(visit, action, user, room=None, notes=''):
    VisitLog.objects.create(
        visit=visit,
        action=action,
        performed_by=user,
        room=room,
        notes=notes,
    )


def calculate_precise_age(dob):
    """
    Returns age in days and category label: 'neonate', 'child', or 'adult'.
    """
    if not dob:
        return 0, 'adult'
    
    today = timezone.localdate()
    delta = today - dob
    days = delta.days
    
    # 13 years in days is roughly 13 * 365.25 = 4748
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if days <= 28:
        return days, 'neonate'
    elif years < 13:
        return years, 'child'
    else:
        return years, 'adult'
