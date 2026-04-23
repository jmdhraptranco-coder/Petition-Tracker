with open('models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The specific section with indentation errors is around indices 300-340.
# Let's rebuild the init_dsr_tables function.

start_marker = "def init_dsr_tables():"
end_marker = "def get_db():"

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if start_marker in line:
        start_idx = i
    if end_marker in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_func = [
        "def init_dsr_tables():\n",
        "    conn = get_db()\n",
        "    try:\n",
        "        cur = dict_cursor(conn)\n",
        "        cur.execute(\"\"\"\n",
        "            CREATE TABLE IF NOT EXISTS dsr_entries (\n",
        "                id SERIAL PRIMARY KEY,\n",
        "                incident_type VARCHAR(50) NOT NULL,\n",
        "                report_date DATE NOT NULL,\n",
        "                circle VARCHAR(100),\n",
        "                place VARCHAR(255),\n",
        "                description TEXT,\n",
        "                transformer_capacity VARCHAR(100),\n",
        "                transformer_category VARCHAR(100),\n",
        "                fire_type VARCHAR(100),\n",
        "                fire_worth_loss DECIMAL(15,2),\n",
        "                fatality_details_json JSONB,\n",
        "                reported_cases_json JSONB,\n",
        "                quality_cases_count INTEGER,\n",
        "                quality_assessment_amount DECIMAL(15,2),\n",
        "                attachment_file VARCHAR(255),\n",
        "                submitted_by INTEGER REFERENCES users(id),\n",
        "                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n",
        "            )\n",
        "        \"\"\")\n",
        "        cur.execute(\"\"\"\n",
        "            CREATE INDEX IF NOT EXISTS idx_dsr_entries_type_date\n",
        "            ON dsr_entries (incident_type, report_date DESC)\n",
        "        \"\"\")\n",
        "        conn.commit()\n",
        "        print('DSR tables initialized successfully.')\n",
        "    except Exception as e:\n",
        "        print(f'Error initializing DSR tables: {e}')\n",
        "        conn.rollback()\n",
        "        raise\n",
        "    finally:\n",
        "        conn.close()\n",
        "\n"
    ]
    lines[start_idx:end_idx] = new_func
    with open('models.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Fixed init_dsr_tables function')
else:
    print('Could not find markers')
