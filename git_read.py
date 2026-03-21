#!/usr/bin/env python3
"""Extract landing.html from specific git commits and write to text files."""
import zlib, os, sys

repo = r'c:/Users/AP TRANSCO/OneDrive - APTRANSCO/Pictures/Petition Tracker with chatbot'
git_dir = os.path.join(repo, '.git')
out_dir = repo

def read_object(sha):
    path = os.path.join(git_dir, 'objects', sha[:2], sha[2:])
    if not os.path.exists(path):
        return None, None
    with open(path, 'rb') as f:
        raw = zlib.decompress(f.read())
    null = raw.index(b'\x00')
    header = raw[:null].decode()
    content = raw[null+1:]
    return header, content

def get_commit_tree(commit_sha):
    h, c = read_object(commit_sha)
    if h is None:
        return None
    for line in c.decode('utf-8', errors='replace').split('\n'):
        if line.startswith('tree '):
            return line[5:].strip()
    return None

def get_tree_entry(tree_sha, name):
    h, c = read_object(tree_sha)
    if h is None:
        return None, None
    i = 0
    while i < len(c):
        sp = c.index(b' ', i)
        nul = c.index(b'\x00', sp+1)
        entry_name = c[sp+1:nul].decode('utf-8', errors='replace')
        sha_bytes = c[nul+1:nul+21]
        entry_sha = sha_bytes.hex()
        i = nul + 21
        if entry_name == name:
            return entry_sha, c[i:i]
    return None, None

def get_file_from_commit(commit_sha, filepath):
    parts = filepath.split('/')
    tree_sha = get_commit_tree(commit_sha)
    if not tree_sha:
        return None
    for part in parts[:-1]:
        sha, _ = get_tree_entry(tree_sha, part)
        if not sha:
            return None
        tree_sha = sha
    blob_sha, _ = get_tree_entry(tree_sha, parts[-1])
    if not blob_sha:
        return None
    h, c = read_object(blob_sha)
    return c

# Commits to check - from the log, ordered from earliest to most recent
# We want to find when the officer animation code changed
commits = [
    ('6d30b503105acece64f323c534b824f4a6cee5c9', 'pre_help_center'),
    ('ee257cb538640edf012ab142380aefcdf12f3778', 'fix_dark_theme'),
    ('57f88a86868a44fae824ed60d8eb7fc41a7ef3be', 'fix_upload'),
    ('1d7cb66fbae928d5937d1a1ed8600b089c73ee8e', 'fix_ereceipt'),
    ('0ed19dc49f4fd8000d53542040919a2c87efd799', 'add_help_center'),
    ('71dafb9b8d8a149d1221beab254aec29ce7f01de', 'chatbot_v1'),
    ('a53892beca1959433b4ea08f9361d4fb3fc7596a', 'chatbot_v2'),
    ('9da8be7a2c4b802b8c5fb2e20b3e550b58ccb0f5', 'sidebar_fix'),
    ('73b99d5941824b1ec71439336c71cb2f146fd0d2', 'chatbot_v3_current'),
]

results = []
for sha, label in commits:
    content = get_file_from_commit(sha, 'templates/landing.html')
    if content is None:
        results.append(f"COMMIT {sha[:8]} ({label}): COULD NOT READ\n")
        continue
    text = content.decode('utf-8', errors='replace')
    size = len(text)
    # Check for keywords
    has_officer_svg = 'officer-icon.svg' in text
    has_inline_svg = '<svg' in text and ('officer' in text.lower() or 'walking' in text.lower() or 'patrol' in text.lower())
    has_officer_css = 'hero-officer' in text
    has_browser_mock = 'browser' in text.lower() or 'dashboard-mock' in text.lower() or 'mock' in text.lower()
    has_walking = 'walk' in text.lower()
    has_svg_anim = '@keyframes' in text and 'svg' in text.lower()

    results.append(f"COMMIT {sha[:8]} ({label}): size={size}, officer_svg={has_officer_svg}, inline_svg={has_inline_svg}, officer_css={has_officer_css}, browser_mock={has_browser_mock}, walking={has_walking}\n")

    # Write full content to file
    out_path = os.path.join(out_dir, f'landing_{label}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)

with open(os.path.join(out_dir, 'git_results.txt'), 'w') as f:
    f.writelines(results)

print("Done!")
