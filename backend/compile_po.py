import struct
import sys
import re

def unescape(s):
    # Very basic unescape for gettext strings
    return s.replace('\\\\', '\\').replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')

def generate_mo(po_path, mo_path):
    messages = {}
    with open(po_path, 'r', encoding='utf-8') as f:
        msgid = None
        msgstr = ""
        in_msgid = False
        in_msgstr = False
        
        for line in f:
            line = line.strip()
            if not line:
                if msgid is not None:
                    messages[unescape(msgid)] = unescape(msgstr)
                msgid = None
                msgstr = ""
                in_msgid = in_msgstr = False
                continue
            
            if line.startswith('msgid "'):
                msgid = line[7:-1]
                in_msgid = True
                in_msgstr = False
            elif line.startswith('msgstr "'):
                msgstr = line[8:-1]
                in_msgid = False
                in_msgstr = True
            elif line.startswith('"') and line.endswith('"'):
                if in_msgid:
                    msgid += line[1:-1]
                elif in_msgstr:
                    msgstr += line[1:-1]
        
        if msgid is not None:
            messages[unescape(msgid)] = unescape(msgstr)

    # Ensure header exists
    if "" not in messages:
        messages[""] = "Content-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n"
    else:
        # Check if charset is in header, if not, force it
        if "charset=" not in messages[""]:
             messages[""] += "Content-Type: text/plain; charset=UTF-8\n"

    sorted_msgids = sorted(messages.keys())
    N = len(sorted_msgids)
    
    id_table = []
    str_table = []
    
    for mid in sorted_msgids:
        mid_b = mid.encode('utf-8')
        mstr_b = messages[mid].encode('utf-8')
        id_table.append((len(mid_b), mid_b + b'\x00'))
        str_table.append((len(mstr_b), mstr_b + b'\x00'))

    id_offsets_start = 28
    str_offsets_start = 28 + 8 * N
    data_start = 28 + 16 * N
    
    id_offsets = []
    pos = data_start
    for length, data in id_table:
        id_offsets.append((length, pos))
        pos += len(data)
        
    str_offsets = []
    for length, data in str_table:
        str_offsets.append((length, pos))
        pos += len(data)

    with open(mo_path, 'wb') as f:
        f.write(struct.pack('<I', 0x950412de)) # Magic
        f.write(struct.pack('<I', 0))          # Revision
        f.write(struct.pack('<I', N))          # N
        f.write(struct.pack('<I', id_offsets_start))
        f.write(struct.pack('<I', str_offsets_start))
        f.write(struct.pack('<I', 0)) # Hash table size
        f.write(struct.pack('<I', 0)) # Hash table offset
        
        for length, offset in id_offsets:
            f.write(struct.pack('<II', length, offset))
        for length, offset in str_offsets:
            f.write(struct.pack('<II', length, offset))
        for _, data in id_table:
            f.write(data)
        for _, data in str_table:
            f.write(data)

if __name__ == "__main__":
    generate_mo(sys.argv[1], sys.argv[2])
