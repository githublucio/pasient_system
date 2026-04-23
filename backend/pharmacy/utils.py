from django.utils.translation import gettext as _

KNOWN_INTERACTIONS = [
    {
        'drugs': ['warfarin', 'aspirin'],
        'severity': 'HIGH',
        'message': _('Warfarin + Aspirin: Increased risk of bleeding.'),
    },
    {
        'drugs': ['metformin', 'alcohol'],
        'severity': 'HIGH',
        'message': _('Metformin + Alcohol: Risk of lactic acidosis.'),
    },
    {
        'drugs': ['amoxicillin', 'methotrexate'],
        'severity': 'HIGH',
        'message': _('Amoxicillin + Methotrexate: Increased methotrexate toxicity.'),
    },
    {
        'drugs': ['ibuprofen', 'aspirin'],
        'severity': 'MODERATE',
        'message': _('Ibuprofen + Aspirin: May reduce aspirin effectiveness.'),
    },
    {
        'drugs': ['ciprofloxacin', 'antacid'],
        'severity': 'MODERATE',
        'message': _('Ciprofloxacin + Antacid: Reduced absorption of ciprofloxacin.'),
    },
    {
        'drugs': ['paracetamol', 'warfarin'],
        'severity': 'MODERATE',
        'message': _('Paracetamol (high dose) + Warfarin: May increase INR.'),
    },
    {
        'drugs': ['omeprazole', 'clopidogrel'],
        'severity': 'HIGH',
        'message': _('Omeprazole + Clopidogrel: Reduced effectiveness of clopidogrel.'),
    },
    {
        'drugs': ['atenolol', 'verapamil'],
        'severity': 'HIGH',
        'message': _('Atenolol + Verapamil: Risk of severe bradycardia and heart block.'),
    },
    {
        'drugs': ['simvastatin', 'clarithromycin'],
        'severity': 'HIGH',
        'message': _('Simvastatin + Clarithromycin: Risk of rhabdomyolysis.'),
    },
    {
        'drugs': ['metronidazole', 'alcohol'],
        'severity': 'HIGH',
        'message': _('Metronidazole + Alcohol: Severe nausea, vomiting (disulfiram-like reaction).'),
    },
    {
        'drugs': ['digoxin', 'amiodarone'],
        'severity': 'HIGH',
        'message': _('Digoxin + Amiodarone: Increased digoxin levels, toxicity risk.'),
    },
    {
        'drugs': ['lithium', 'ibuprofen'],
        'severity': 'HIGH',
        'message': _('Lithium + Ibuprofen: Increased lithium levels, toxicity risk.'),
    },
    {
        'drugs': ['amlodipine', 'simvastatin'],
        'severity': 'MODERATE',
        'message': _('Amlodipine + Simvastatin: Increased statin levels. Max simvastatin 20mg.'),
    },
    {
        'drugs': ['fluconazole', 'warfarin'],
        'severity': 'HIGH',
        'message': _('Fluconazole + Warfarin: Significantly increased INR and bleeding risk.'),
    },
    {
        'drugs': ['erythromycin', 'theophylline'],
        'severity': 'MODERATE',
        'message': _('Erythromycin + Theophylline: Increased theophylline levels.'),
    },
    {
        'drugs': ['captopril', 'potassium'],
        'severity': 'MODERATE',
        'message': _('ACE Inhibitor + Potassium: Risk of hyperkalemia.'),
    },
    {
        'drugs': ['enalapril', 'potassium'],
        'severity': 'MODERATE',
        'message': _('ACE Inhibitor + Potassium: Risk of hyperkalemia.'),
    },
    {
        'drugs': ['doxycycline', 'antacid'],
        'severity': 'MODERATE',
        'message': _('Doxycycline + Antacid: Reduced absorption of doxycycline.'),
    },
    {
        'drugs': ['rifampicin', 'oral contraceptive'],
        'severity': 'HIGH',
        'message': _('Rifampicin + Oral Contraceptive: Reduced contraceptive effectiveness.'),
    },
    {
        'drugs': ['phenytoin', 'carbamazepine'],
        'severity': 'MODERATE',
        'message': _('Phenytoin + Carbamazepine: Altered levels of both drugs.'),
    },
]


def check_drug_interactions(medicine_names):
    """
    Check for known drug interactions given a list of medicine names.
    Returns a list of warning dicts: [{'severity': 'HIGH', 'message': '...'}]
    """
    warnings = []
    normalized = [name.lower().strip() for name in medicine_names if name]
    
    for interaction in KNOWN_INTERACTIONS:
        matched = all(
            any(drug in med_name for med_name in normalized)
            for drug in interaction['drugs']
        )
        if matched:
            warnings.append({
                'severity': interaction['severity'],
                'message': interaction['message'],
            })
    
    return warnings
