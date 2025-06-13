import os
import hashlib
import pickle
import zlib

def init_vcs():
    os.makedirs('.pvcs', exist_ok=True)
    print("VCS initialized.")
    
def load_message_map():
    if not os.path.exists('.pvcs/ref'):
        return {}
    with open('.pvcs/ref', 'rb') as f:
        compressed_ref = f.read()
        pickle.loads(zlib.decompress(compressed_ref))
        return pickle.load(f)
    
def save_message_map(message_map):
    with open('.pvcs/ref', 'wb') as f:
        compressed_ref = zlib.compress(pickle.dumps(message_map))
        f.write(compressed_ref)

def snapshot(directory, message=None):
    snapshot_hash = hashlib.sha256()
    snapshot_data = {'files': {}}

    for root, _, files in os.walk(directory):
        for file in files:
            if '.pvcs' in os.path.join(root, file):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                content = f.read()
                snapshot_hash.update(content)
                snapshot_data['files'][file_path] = content

    hash_digest = snapshot_hash.hexdigest() 
    snapshot_data['file_list'] = list(snapshot_data['files'].keys())
    
    if message:
        ref = load_message_map()
        ref[message] = hash_digest
        save_message_map(ref)
        
    with open(f'.pvcs/{hash_digest}', 'wb') as f:
        compressed_data = zlib.compress(pickle.dumps(snapshot_data))
        f.write(compressed_data)
    print(f"Snapshot created with hash {hash_digest}")

def revert_to_snapshot_by_digest(hash_digest):
    snapshot_path = f'.pvcs/{hash_digest}'
    if not os.path.exists(snapshot_path):
        print("Snapshot does not exist.")
        return
    with open(snapshot_path, 'rb') as f:
        compressed_data = f.read()
        snapshot_data = pickle.loads(zlib.decompress(compressed_data))
    for file_path, content in snapshot_data['files'].items():
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(content)
    current_files = set()
    for root, dirs, files in os.walk('.', topdown=True):
        if '.pvcs' in root:
            continue
        for file in files:
            current_files.add(os.path.join(root, file))
    snapshot_files = set(snapshot_data['file_list'])
    files_to_delete = current_files - snapshot_files
    for file_path in files_to_delete:
        os.remove(file_path)
        print(f"Removed {file_path}")
    print(f"Reverted to snapshot {hash_digest}")
    
def revert_to_snapshot_by_message(message):
    message_map = load_message_map()
    hash_digest = message_map.get(message)
    if not hash_digest:
        print(f"No snapshot found for message: '{message}'")
        return
    revert_to_snapshot_by_digest(hash_digest)

if __name__ == "__main__":
    import sys
    command = sys.argv[1]
    if command == "init":
        init_vcs()
    elif command == "snapshot":
        if "-m" in sys.argv:
            snapshot('.', message=sys.argv[3])
        else:
            snapshot('.')
    elif command == "revert":
        if "-m" in sys.argv:
            revert_to_snapshot_by_message(sys.argv[3])
        else:
            revert_to_snapshot_by_digest(sys.argv[2])
    else:
        print("Unknown command.")