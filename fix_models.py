import re

with open('models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find start of create_dsr_entry
start_marker = '\ndef create_dsr_entry(data, submitted_by):'
end_marker = '\ndef get_dsr_entries('

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f'Marker not found: start={start_idx}, end={end_idx}')
    exit(1)

print(f'Function found from {start_idx} to {end_idx}')

new_func = """
def create_dsr_entry(data, submitted_by):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute(\"\"\"
            INSERT INTO dsr_entries (
                incident_type, report_date, circle, place, description,
                transformer_capacity, transformer_category,
                fire_type, fire_worth_loss,
                fatality_details_json, reported_cases_json,
                quality_cases_count, quality_assessment_amount,
                attachment_file, submitted_by
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            ) RETURNING id
        \"\"\", (
            data.get('incident_type'),
            data.get('report_date'),
            data.get('circle') or None,
            data.get('place') or None,
            data.get('description') or None,
            data.get('transformer_capacity') or None,
            data.get('transformer_category') or None,
            data.get('fire_type') or None,
            data.get('fire_worth_loss') or None,
            data.get('fatality_details_json') or None,
            data.get('reported_cases_json') or None,
            data.get('quality_cases_count') or None,
            data.get('quality_assessment_amount') or None,
            data.get('attachment_file') or None,
            submitted_by,
        ))
        row = cur.fetchone()
        conn.commit()
        return row['id'] if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
"""

# ensure new_func has exactly one newline at start to match the replaced block's start
if not new_func.startswith('\n'):
    new_func = '\n' + new_func.lstrip()

new_content = content[:start_idx] + new_func + content[end_idx:]

with open('models.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done')
