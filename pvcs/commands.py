from pvcs.core import snapshot, revert_to_digest, revert_to_message
from pvcs.storage import save_ref, load_ref
import os

def init():
    os.makedirs('.pvcs/objects', exist_ok=True)
    print("VCS initialized.")

def take_snapshot(message=None):
    snapshot('.', message=message)

def revert(hash_or_message, is_message=False):
    if is_message:
        revert_to_message(hash_or_message)
    else:
        revert_to_digest(hash_or_message)
