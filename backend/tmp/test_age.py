from datetime import date, timedelta
import sys
import os

# Mock Django timezone
class MockTimezone:
    def localdate(self):
        return date(2026, 4, 1)

timezone = MockTimezone()

def calculate_precise_age(dob):
    if not dob:
        return 0, 'adult'
    
    today = timezone.localdate()
    delta = today - dob
    days = delta.days
    
    # 13 years calculation
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    
    if days <= 28:
        return days, 'neonate'
    elif years <= 13:
        return years, 'child'
    else:
        return years, 'adult'

# Test cases
test_cases = [
    (date(2026, 3, 20), (12, 'neonate')),
    (date(2026, 3, 4), (28, 'neonate')),
    (date(2026, 3, 3), (29, 'child')),
    (date(2013, 4, 1), (13, 'child')),
    (date(2013, 3, 31), (13, 'adult')), # Correct? No, 2026-2013 = 13. Birthday was yesterday. So 13 years old.
]

# Let's re-check the 13 years logic.
# If today is 2026-04-01:
# DOB 2013-04-01 -> 13 years old (Birthday is today). Category CHILD? 
# "Child: 28 days - 13 years". ">13 years: Adult".
# If DOB is 2013-03-31, they are 13 years and 1 day. So ADULT.

for dob, expected in test_cases:
    res = calculate_precise_age(dob)
    print(f"DOB: {dob}, Age: {res}, Expected: {expected}")
