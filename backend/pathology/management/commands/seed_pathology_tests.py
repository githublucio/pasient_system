from django.core.management.base import BaseCommand
from pathology.models import PathologyTest

class Command(BaseCommand):
    help = 'Seeds initial pathology test catalog into the system'

    def handle(self, *args, **kwargs):
        tests = [
            "CBC", "Glukosa", "Uric Acid", "Total cholesterol", "Triglyceride", "LDL", "HDL", 
            "Na,K", "Magnesium", "Bicarbonat", "ALT", "AST", "GGT", "ALKP", "Total Protein", 
            "Albumin", "Globulin", "Total Bilirubin/Indirect", "Direct", "Urea", "Creatinin", "Calcium"
        ]

        PathologyTest.objects.all().delete()
        
        objects_to_create = []
        for index, test_name in enumerate(tests, start=1):
            objects_to_create.append(PathologyTest(name=test_name, order=index))
            
        PathologyTest.objects.bulk_create(objects_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(tests)} pathology chemistry tests.'))
