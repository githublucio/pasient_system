from django.core.management.base import BaseCommand
from radiology.models import RadiologyTest

class Command(BaseCommand):
    help = 'Seeds initial radiology test catalog into the system'

    def handle(self, *args, **kwargs):
        tests = [
            "Thorax AP/PA", "Thorax Ap no Lateral", "BNO", "BNO 3 Posisi", "Schadel AP dan Lateral", "Mastoid", "SPN", 
            "Os Nasal", "TMJ", "Mandibula", "Clavicula AP", "Humerus AP No Lateral", "Shoulder Joint AP", "Antebrachi AP no Lateral", 
            "Manus AP no Lateral", "Pelvis AP", "Femur AP no Literal", "Elbow Joint AP no Lateral", "Cruris AP no Lateral", "Wrist Joint AP no Lateral", 
            "Hip Joint no Lateral", "Genu AP no Lateral", "Ankle Joint AP no Lateral", "Pedis AP no Lateral", "Bone Age", "Vertebra Cervical AP/Lateral", 
            "STL (Soft Tissue Leher)", "Vertebre Thoracalis AP/Lateral", "Thoracolumbal AP/Lateral", "Lumbosacral AP/Lateral"
        ]

        # Ensure we don't accidentally duplicate
        RadiologyTest.objects.all().delete()
        
        objects_to_create = []
        for index, test_name in enumerate(tests, start=1):
            objects_to_create.append(RadiologyTest(name=test_name, order=index))
            
        RadiologyTest.objects.bulk_create(objects_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(tests)} radiology tests.'))
