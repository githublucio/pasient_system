import os
import django
import time
from django.db.models import Q

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_core.settings')
django.setup()

from patients.models import Patient

def verify_performance():
    print(f"--- Verifying Performance on {Patient.objects.count()} Patients ---")
    
    test_queries = ["maria", "joao", "soares", "da costa", "77"]
    
    for query in test_queries:
        start_time = time.time()
        results = Patient.objects.filter(
            Q(full_name__icontains=query) | 
            Q(patient_id__icontains=query) | 
            Q(phone_number__icontains=query)
        )[:50]
        count = results.count()
        duration = (time.time() - start_time) * 1000
        
        print(f"Search for '{query}': {count} results found in {duration:.2f}ms")

if __name__ == "__main__":
    verify_performance()
