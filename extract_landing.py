import zlib, os, sys

repo = r'c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot'
git_dir = os.path.join(repo, '.git')

def read_object(sha):
    path = os.path.join(git_dir, 'objects', sha[:2], sha[2:])
    with open(path, 'rb') as f:
        data = zlib.decompress(f.read())
    nul = data.index(b'\x00')
    return data[:nul].decode(), data[nul+1:]

def get_tree(commit_sha):
    _, body = read_object(commit_sha)
    for line in body.decode('utf-8', errors='replace').split('\n'):
        if line.startswith('tree '):
            return line[5:].strip()

def find_blob(tree_sha, target_parts):
    _, body = read_object(tree_sha)
    i = 0
    while i < len(body):
        sp = body.index(b' ', i)
        nul = body.index(b'\x00', sp)
        name = body[sp+1:nul].decode('utf-8', errors='replace')
        sha = body[nul+1:nul+21].hex()
        i = nul + 21
        if name == target_parts[0]:
            if len(target_parts) == 1:
                return sha
            else:
                return find_blob(sha, target_parts[1:])
    return None

# HEAD commit
head_sha = '73b99d5941824b1ec71439336c71cb2f146fd0d2'
tree_sha = get_tree(head_sha)
print('Tree:', tree_sha)

blob_sha = find_blob(tree_sha, ['templates', 'landing.html'])
print('Blob:', blob_sha)

if blob_sha:
    _, content = read_object(blob_sha)
    out_path = os.path.join(repo, 'landing_git_head.html')
    with open(out_path, 'wb') as f:
        f.write(content)
    print(f'Saved {len(content)} bytes to landing_git_head.html')
