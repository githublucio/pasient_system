import os
import re
import gettext
from collections import Counter

po_path = 'locale/tet/LC_MESSAGES/django.po'
mo_path = 'locale/tet/LC_MESSAGES/django.mo'

def debug():
    if not os.path.exists(po_path):
        print(f"Error: {po_path} not found")
        return

    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all msgids
    ids = re.findall(r'^msgid \"(.*?)\"', content, re.MULTILINE)
    print(f"Total msgids in PO: {len(ids)}")

    # Check for duplicates
    counts = Counter(ids)
    dups = [k for k, v in counts.items() if v > 1]
    if dups:
        print(f"Duplicate msgids found: {dups}")
    else:
        print("No duplicate msgids found.")

    # Check for specific strings
    search_strings = ["Dashboard", "Clinic Dashboard", "Patients Today", "Gender", "Year"]
    for s in search_strings:
        found = s in ids
        print(f"'{s}' in PO: {found}")

    # Check the MO file
    if os.path.exists(mo_path):
        try:
            with open(mo_path, 'rb') as f:
                t = gettext.GNUTranslations(f)
            print(f"Total keys in MO: {len(t._catalog.keys()) if hasattr(t, '_catalog') else 'N/A'}")
            
            for s in search_strings:
                trans = t.gettext(s)
                print(f"MO Translation for '{s}': {trans}")
        except Exception as e:
            print(f"Error reading MO: {e}")
    else:
        print("Error: MO file not found")

if __name__ == "__main__":
    debug()
