import hashlib
import os
import pickle
import zlib

from pvcs.ignore import is_ignored, load_ignore_patterns
from pvcs.storage import build_snapshot_obj, decompress, load_head, load_ref, load_snapshot_obj, save_head, save_ref, store_snapshot_obj


def hash_blob(content):
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha256(header + content).hexdigest()

def store_blob(content):
    blob_hash = hash_blob(content)
    blob_path = os.path.join('.pvcs/objects', blob_hash)
    if not os.path.exists(blob_path):
        compressed_blob = zlib.compress(content)
        with open(blob_path, 'wb') as f:
            f.write(compressed_blob)
    return blob_hash

def changes_to_track(tree_hash):
    last_snap_hash = load_head()
    if not last_snap_hash:
        return True
    last_snap_path = os.path.join('.pvcs/objects', last_snap_hash)
    with open(last_snap_path, 'rb') as f:
        last_snap_data = decompress(f.read())
    last_tree_hash = last_snap_data['tree']

    if last_tree_hash == tree_hash:
        print("No changes since last snapshot.")
        return False
    return True

def snapshot(directory, message=None):
    snapshot_data = {'files': {}}
    ignored_contents = load_ignore_patterns()

    for root, dirs, files in os.walk(directory):
        #ignore dirs and subdirs
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), ignored_contents)]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, directory)
            if is_ignored(rel_path, ignored_contents):                
                continue
            
            with open(file_path, 'rb') as f:
                content = f.read()
                blob_hash = store_blob(content)
                snapshot_data['files'][rel_path] = blob_hash

    parent = load_head()
    
    tree_bytes = pickle.dumps(snapshot_data)
    tree_hash  = hashlib.sha256(tree_bytes).hexdigest()
    if not changes_to_track(tree_hash):
        return
    
    tree_obj   = os.path.join('.pvcs', 'objects', tree_hash)
    if not os.path.exists(tree_obj):
        with open(tree_obj, 'wb') as f:
            f.write(zlib.compress(tree_bytes))
            
    snapshot_obj  = build_snapshot_obj(tree_hash, parent, message)
    snapshot_hash = store_snapshot_obj(snapshot_obj)
    
    if message:
        ref = load_ref()
        ref[message] = snapshot_hash
        save_ref(ref)
        
    save_head(snapshot_hash)
    print(f"Snapshot created with hash {snapshot_hash}")
    
def restore_files(snapshot_files):
    for rel_path, blob_hash in snapshot_files.items():
        blob_path = os.path.join('.pvcs', 'objects', blob_hash)
        with open(blob_path, 'rb') as bf:
            content = zlib.decompress(bf.read())
        abs_path = os.path.join('.', rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'wb') as out:
            out.write(content)

def remove_untracked_files(snapshot_files):
    current_files = set()
    for root, _, files in os.walk('.'):
        if is_ignored(root, patterns=['.pvcs', '.git']):
            continue
        for f in files:
            current_files.add(os.path.join(root, f))

    desired_paths = set(os.path.join('.', p) for p in snapshot_files)
    for path in current_files - desired_paths:
        os.remove(path)

def revert_to_digest(snapshot_hash):
    try:
        snapshot = load_snapshot_obj(snapshot_hash)
    except FileNotFoundError:
        print(f"Snapshot {snapshot_hash} not found.")
        return

    tree_hash = snapshot.get("tree")
    tree_path = os.path.join('.pvcs', 'objects', tree_hash)
    if not os.path.exists(tree_path):
        print(f"Tree object {tree_hash} not found.")
        return

    with open(tree_path, 'rb') as tf:
        tree_data = decompress(tf.read())
    snapshot_files = tree_data['files']
    
    remove_untracked_files(snapshot_files)
    restore_files(snapshot_files)
    save_head(snapshot_hash)

    print(f"Reverted to snapshot {snapshot_hash}")

def revert_to_message(message):
    message_map = load_ref()
    snapshot_hash = message_map.get(message)
    if not snapshot_hash:
        print(f"No snapshot found for message: '{message}'")
        return
    revert_to_digest(snapshot_hash)

def log(n=10):
    head = load_head()
    if not head:
        print("No snaps yet.")
        return

    count = 0
    current = head
    print(f"{'SNap':<64}  {'DATE':19}  MESSAGE")
    print("-"*64 + "  " + "-"*19 + "  " + "-"*10)

    while current and count < n:
        try:
            snapshot = load_snapshot_obj(current)
        except FileNotFoundError:
            break

        ts = snapshot.get("timestamp", "")
        msg = snapshot.get("message", "")
        print(f"{current}  {ts}  '{msg or '(no message)'}'")

        current = snapshot.get("parent")
        count += 1
    print()