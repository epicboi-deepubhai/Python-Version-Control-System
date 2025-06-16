import os
import pickle
import zlib

def compress(obj):
    return zlib.compress(pickle.dumps(obj))

def decompress(data):
    return pickle.loads(zlib.decompress(data))

def save_snapshot(data, path):
    with open(path, 'wb') as f:
        f.write(compress(data))

def load_snapshot(path):
    with open(path, 'rb') as f:
        return decompress(f.read())

def save_ref(ref_map, path='.pvcs/ref'):
    with open(path, 'wb') as f:
        f.write(compress(ref_map))

def load_ref(path='.pvcs/ref'):
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return decompress(f.read())
