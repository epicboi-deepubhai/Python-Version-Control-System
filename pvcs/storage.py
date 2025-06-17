import hashlib
import os
import pickle
import time
import zlib

def compress(obj):
    return zlib.compress(pickle.dumps(obj))

def decompress(data):
    return pickle.loads(zlib.decompress(data))

def save_ref(ref_map, path='.pvcs/ref'):
    with open(path, 'wb') as f:
        f.write(compress(ref_map))

def load_ref(path='.pvcs/ref'):
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return decompress(f.read())
    
def load_head(path='.pvcs/HEAD'):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read().strip()
    return None

def save_head(commit_hash):
    with open('.pvcs/HEAD', 'w') as f:
        f.write(commit_hash)

def build_snapshot_obj(tree_hash, parent_hash=None, message=None):
    return {
        "tree":      tree_hash,
        "parent":    parent_hash,
        "message":   message or "",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    }

def store_snapshot_obj(snapshot_obj):
    data = pickle.dumps(snapshot_obj)
    snapshot_hash = hashlib.sha256(data).hexdigest()
    obj_path = os.path.join('.pvcs', 'objects', snapshot_hash)
    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as f:
            f.write(zlib.compress(data))
    return snapshot_hash

def load_snapshot_obj(commit_hash):
    obj_path = os.path.join('.pvcs', 'objects', commit_hash)
    if not os.path.exists(obj_path):
        raise FileNotFoundError(f"Commit object {commit_hash} not found")

    with open(obj_path, 'rb') as f:
        compressed = f.read()
    data = zlib.decompress(compressed)
    return pickle.loads(data)