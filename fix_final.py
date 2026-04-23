with open('models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(len(lines)):
    if '            ON dsr_entries (incident_type, report_date DESC)' in lines[i]:
        # indices i is line 316.
        # We replace the problematic lines.
        lines[i+1] = '        """)\n'
        lines[i+2] = '        conn.commit()\n'
        lines[i+3] = '    except Exception as e:\n'
        lines[i+4] = "        print(f'Error: {e}')\n"
        lines[i+5] = '        conn.rollback()\n'
        lines[i+6] = '        raise\n'
        lines[i+7] = '    finally:\n'
        lines[i+8] = '        conn.close()\n'
        
        # Clear until get_db
        j = i + 9
        while j < len(lines) and 'def get_db():' not in lines[j]:
             lines[j] = ''
        break

with open('models.py' , 'w', encoding='utf-8') as f:
    f.writelines([l for l in lines if l != ''])
