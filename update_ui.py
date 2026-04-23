import os, re
base_file = 'templates/base.html'
if os.path.exists(base_file):
    with open(base_file, 'r', encoding='utf-8') as f: content = f.read()
    new_link = """<a href="{{ url_for('dsr_dashboard') }}" class="nav-item {% if request.endpoint == 'dsr_dashboard' %}active{% endif %}">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 14l3-3 3 2 4-5"/></svg>
    <span>DSR Dashboard</span>
</a>"""
    if 'dsr_dashboard' not in content:
        import re
        pattern = re.compile(r'(<a href="{{ url_for\(\'dsr_list\'\) }}".*?</a>)', re.DOTALL)
        if pattern.search(content):
            new_content = pattern.sub(r'\1\n' + new_link, content)
            with open(base_file, 'w', encoding='utf-8') as f: f.write(new_content)
            print('Updated base.html')
        else: print('Could not find DSR link in base.html')
    else: print('DSR Dashboard link already exists in base.html')

list_file = 'templates/dsr_list.html'
if os.path.exists(list_file):
    with open(list_file, 'r', encoding='utf-8') as f: content = f.read()
    quick = '<a href="{{ url_for(\'dsr_dashboard\') }}" class="btn btn-outline btn-sm">Open DSR Dashboard</a>'
    if 'Open DSR Dashboard' not in content:
        if '<div class="petitions-toolbar">' in content:
            new_content = content.replace('<div class="petitions-toolbar">', '<div class="petitions-toolbar">\n        ' + quick)
            with open(list_file, 'w', encoding='utf-8') as f: f.write(new_content)
            print('Updated dsr_list.html')
        else: print('Could not find toolbar in dsr_list.html')
    else: print('Open DSR Dashboard exists')
