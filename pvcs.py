import os
import hashlib
import pickle
import zlib

def init_vcs():
    os.makedirs('.pvcs/objects', exist_ok=True)
    print("VCS initialized.")

def load_message_map():
    if not os.path.exists('.pvcs/ref'):
        return {}
    with open('.pvcs/ref', 'rb') as f:
        compressed_ref = f.read()
        return pickle.loads(zlib.decompress(compressed_ref))
    
def save_message_map(message_map):
    with open('.pvcs/ref', 'wb') as f:
        compressed_ref = zlib.compress(pickle.dumps(message_map))
        f.write(compressed_ref)

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

    for root, _, files in os.walk(directory):
        if '.pvcs' in root or '.git' in root: #annoying git kept giving errors
            continue
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, directory)
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
        ref = load_message_map()
        ref[message] = snapshot_hash
        save_message_map(ref)

    print(f"Snapshot created with hash {snapshot_hash}")

def revert_to_snapshot_by_digest(snapshot_hash):
    snapshot_path = f".pvcs/{snapshot_hash}"
    if not os.path.exists(snapshot_path):
        print("Snapshot does not exist.")
        return
    with open(snapshot_path, 'rb') as f:
        compressed_data = f.read()
        snapshot_data = pickle.loads(zlib.decompress(compressed_data))

    current_files = set()
    for root, _, files in os.walk('.'):
        if '.pvcs' in root:
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

def revert_to_snapshot_by_message(message):
    message_map = load_message_map()
    snapshot_hash = message_map.get(message)
    if not snapshot_hash:
        print(f"No snapshot found for message: '{message}'")
        return
    revert_to_snapshot_by_digest(snapshot_hash)

if __name__ == "__main__":
    import sys
    command = sys.argv[1]
    if command == "init":
        init_vcs()
    elif command == "snapshot":
        message = None
        if "-m" in sys.argv:
            try:
                msg_index = sys.argv.index("-m") + 1
                message = sys.argv[msg_index]
            except IndexError:
                print("Missing message after -m")
        snapshot('.', message)
    elif command == "revert":
        if "-m" in sys.argv:
            try:
                msg_index = sys.argv.index("-m") + 1
                revert_to_snapshot_by_message(sys.argv[msg_index])
            except IndexError:
                print("Missing message after -m")
        elif len(sys.argv) > 2:
            revert_to_snapshot_by_digest(sys.argv[2])
        else:
            print("Missing snapshot hash or -m flag")
    else:
        print("Unknown command.")
