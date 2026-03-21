import zlib, os, struct, sys

repo = r'c:/Users/AP TRANSCO/OneDrive - APTRANSCO/Pictures/Petition Tracker with chatbot'
git_dir = os.path.join(repo, '.git')

def read_loose_object(sha):
    path = os.path.join(git_dir, 'objects', sha[:2], sha[2:])
    if not os.path.exists(path):
        return None, None
    with open(path, 'rb') as f:
        data = zlib.decompress(f.read())
    null = data.index(b'\x00')
    header = data[:null].decode()
    content = data[null+1:]
    return header, content

def read_packed_object(sha):
    """Search pack files for the object"""
    pack_dir = os.path.join(git_dir, 'objects', 'pack')
    if not os.path.exists(pack_dir):
        return None, None
    for fname in os.listdir(pack_dir):
        if fname.endswith('.idx'):
            pack_base = fname[:-4]
            idx_path = os.path.join(pack_dir, fname)
            pack_path = os.path.join(pack_dir, pack_base + '.pack')
            result = search_pack(sha, idx_path, pack_path)
            if result:
                return result
    return None, None

def read_object(sha):
    h, c = read_loose_object(sha)
    if h is not None:
        return h, c
    return read_packed_object(sha)

def get_commit_tree(commit_sha):
    h, c = read_object(commit_sha)
    if h is None:
        print(f"Could not read commit {commit_sha}")
        return None
    for line in c.decode('utf-8', errors='replace').split('\n'):
        if line.startswith('tree '):
            return line[5:].strip()
    return None

def get_tree_entry(tree_sha, name):
    h, c = read_object(tree_sha)
    if h is None:
        print(f"Could not read tree {tree_sha}")
        return None
    # Parse tree: mode SP name NUL sha(20 bytes)
    i = 0
    while i < len(c):
        sp = c.index(b' ', i)
        mode = c[i:sp].decode()
        nul = c.index(b'\x00', sp+1)
        entry_name = c[sp+1:nul].decode('utf-8', errors='replace')
        sha_bytes = c[nul+1:nul+21]
        entry_sha = sha_bytes.hex()
        i = nul + 21
        if entry_name == name:
            return entry_sha, mode
    return None, None

def get_file_from_commit(commit_sha, filepath):
    parts = filepath.split('/')
    tree_sha = get_commit_tree(commit_sha)
    if not tree_sha:
        return None
    for part in parts[:-1]:
        sha, mode = get_tree_entry(tree_sha, part)
        if not sha:
            return None
        tree_sha = sha
    blob_sha, mode = get_tree_entry(tree_sha, parts[-1])
    if not blob_sha:
        return None
    h, c = read_object(blob_sha)
    if h is None:
        return None
    return c

# Commits from the log (earliest that might have officer animation)
commits = [
    ('110e702090a25f2ca658ebd61fc2751a49e2c69f', 'Initial commit'),
    ('66df2b96d2b5fbd587c082b5a54e879c5cd52b49', 'Add user profile management'),
    ('0ed19dc49f4fd8000d53542040919a2c87efd799', 'Add help center'),
    ('6d30b503105acece64f323c534b824f4a6cee5c9', 'Implement overdue SLA'),
    ('ee257cb538640edf012ab142380aefcdf12f3778', 'Fix dark theme'),
    ('57f88a86868a44fae824ed60d8eb7fc41a7ef3be', 'Fix upload file handling'),
    ('1d7cb66fbae928d5937d1a1ed8600b089c73ee8e', 'Fix e-receipt upload'),
]

for sha, msg in commits:
    print(f"\n{'='*60}")
    print(f"Commit: {sha[:8]} - {msg}")
    content = get_file_from_commit(sha, 'templates/landing.html')
    if content is None:
        print("  -> Could not read file (may be in pack file)")
        continue
    text = content.decode('utf-8', errors='replace')
    # Search for police officer keywords
    keywords = ['officer', 'police', 'walking', 'patrol', 'figure', 'officer-icon', 'stickman', 'hero-visual', 'hero-image', 'hero-right']
    found = False
    for kw in keywords:
        if kw.lower() in text.lower():
            print(f"  -> Found keyword: '{kw}'")
            found = True
    if not found:
        print("  -> No police officer keywords found")
    # Show size
    print(f"  -> File size: {len(text)} chars")
