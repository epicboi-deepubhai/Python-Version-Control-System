import hashlib
import os
import pickle
from posixpath import relpath
import zlib

from pvcs.ignore import is_ignored, load_ignore_patterns
from pvcs.storage import load_ref, save_ref


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

    snapshot_pickle = pickle.dumps(snapshot_data)
    snapshot_hash = hashlib.sha256(snapshot_pickle).hexdigest()

    with open(os.path.join('.pvcs', snapshot_hash), 'wb') as f:
        compressed_data = zlib.compress(snapshot_pickle)
        f.write(compressed_data)

    if message:
        ref = load_ref()
        ref[message] = snapshot_hash
        save_ref(ref)

    print(f"Snapshot created with hash {snapshot_hash}")

def revert_to_digest(snapshot_hash):
    snapshot_path = f".pvcs/{snapshot_hash}"
    if not os.path.exists(snapshot_path):
        print("Snapshot does not exist.")
        return
    with open(snapshot_path, 'rb') as f:
        compressed_data = f.read()
        snapshot_data = pickle.loads(zlib.decompress(compressed_data))

    current_files = set()
    for root, _, files in os.walk('.'):
        if is_ignored(root, patterns=['.pvcs', '.git']):
            continue
        for file in files:
            path = os.path.join(root, file)
            current_files.add(path)

    snapshot_files = set(os.path.join('.', rel_path) for rel_path in snapshot_data['files'].keys())
    
    files_to_delete = current_files - snapshot_files
    for file_path in files_to_delete:
        os.remove(file_path)

    for rel_path, blob_hash in snapshot_data['files'].items():
        blob_path = os.path.join('.pvcs/objects', blob_hash)
        with open(blob_path, 'rb') as f:
            content = zlib.decompress(f.read())
        abs_path = os.path.join('.', rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'wb') as f:
            f.write(content)

    print(f"Reverted to snapshot {snapshot_hash}")

def revert_to_message(message):
    message_map = load_ref()
    snapshot_hash = message_map.get(message)
    if not snapshot_hash:
        print(f"No snapshot found for message: '{message}'")
        return
    revert_to_digest(snapshot_hash)
