import gettext
import sys

def test_mo(mo_path):
    try:
        with open(mo_path, 'rb') as f:
            t = gettext.GNUTranslations(f)
            print("Charset:", t._charset)
            print("Messages:", len(t._catalog))
            for k, v in list(t._catalog.items())[:10]:
                print(f"  {k!r} -> {v!r}")
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mo(sys.argv[1])
