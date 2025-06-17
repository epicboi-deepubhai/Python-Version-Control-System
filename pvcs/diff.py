import os
import hashlib
import zlib
from pvcs.storage import load_head, load_snapshot_obj, decompress
from pvcs.ignore import is_ignored, load_ignore_patterns

def hash_blob(content):
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha256(header + content).hexdigest()

def get_working_directory_state(directory='.'):
    working_files = {}
    ignored_contents = load_ignore_patterns()
    
    for root, dirs, files in os.walk(directory):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), ignored_contents)]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, directory)
            
            if is_ignored(rel_path, ignored_contents):
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    blob_hash = hash_blob(content)
                    working_files[rel_path] = blob_hash
            except (IOError, OSError):
                # Skip files that can't be read
                continue
    
    return working_files

def get_commit_files(commit_hash):
    if not commit_hash:
        return {}
    
    try:
        snapshot = load_snapshot_obj(commit_hash)
        tree_hash = snapshot.get("tree")
        tree_path = os.path.join('.pvcs', 'objects', tree_hash)
        
        with open(tree_path, 'rb') as f:
            tree_data = decompress(f.read())
        
        return tree_data.get('files', {})
    except FileNotFoundError:
        print(f"Commit {commit_hash} not found.")
        return {}

def compare_file_states(old_files, new_files):
    old_set = set(old_files.keys())
    new_set = set(new_files.keys())
    
    added = new_set - old_set
    removed = old_set - new_set
    common = old_set & new_set
    
    modified = []
    for file_path in common:
        if old_files[file_path] != new_files[file_path]:
            modified.append(file_path)
    
    return sorted(added), sorted(removed), sorted(modified)

def print_diff_summary(added, removed, modified, from_desc, to_desc):
    total_changes = len(added) + len(removed) + len(modified)
    
    if total_changes == 0:
        print(f"No differences between {from_desc} and {to_desc}")
        return
    
    print(f"Differences between {from_desc} and {to_desc}:")
    print("-" * 50)
    
    if added:
        print(f"\nAdded files ({len(added)}):")
        for file_path in added:
            print(f"  + {file_path}")
    
    if removed:
        print(f"\nRemoved files ({len(removed)}):")
        for file_path in removed:
            print(f"  - {file_path}")
    
    if modified:
        print(f"\nModified files ({len(modified)}):")
        for file_path in modified:
            print(f"  M {file_path}")
    
    print(f"\n{total_changes} file(s) changed")

def resolve_commit_reference(ref):
    if len(ref) >= 7:
        try:
            load_snapshot_obj(ref)
            return ref
        except FileNotFoundError:
            pass
    
    # Try as message reference
    from pvcs.storage import load_ref
    message_map = load_ref()
    if ref in message_map:
        return message_map[ref]
    
    print(f"Could not resolve reference: {ref}")
    return None

def diff(commit1=None, commit2=None):
    
    if commit1 is None and commit2 is None:
        # compare HEAD with working directory
        head_hash = load_head()
        if not head_hash:
            print("No commits found. Working directory compared to empty state.")
            working_files = get_working_directory_state()
            added, removed, modified = compare_file_states({}, working_files)
            print_diff_summary(added, removed, modified, "empty state", "working directory")
            return
        
        head_files = get_commit_files(head_hash)
        working_files = get_working_directory_state()
        added, removed, modified = compare_file_states(head_files, working_files)
        print_diff_summary(added, removed, modified, f"HEAD ({head_hash[:8]})", "working directory")
        
    elif commit2 is None:
        # compare snapshot with working directory
        commit_hash = resolve_commit_reference(commit1)
        if not commit_hash:
            return
        
        commit_files = get_commit_files(commit_hash)
        working_files = get_working_directory_state()
        added, removed, modified = compare_file_states(commit_files, working_files)
        print_diff_summary(added, removed, modified, f"commit {commit_hash[:8]}", "working directory")
        
    else:
        # both snaps specified
        hash1 = resolve_commit_reference(commit1)
        hash2 = resolve_commit_reference(commit2)
        
        if not hash1 or not hash2:
            return
        
        files1 = get_commit_files(hash1)
        files2 = get_commit_files(hash2)
        added, removed, modified = compare_file_states(files1, files2)
        print_diff_summary(added, removed, modified, f"commit {hash1[:8]}", f"commit {hash2[:8]}")


def show_file_diff(file_path, old_hash, new_hash):
    print(f"\nDiff for {file_path}:")
    print("-" * 40)
    
    try:
        if old_hash:
            old_blob_path = os.path.join('.pvcs', 'objects', old_hash)
            with open(old_blob_path, 'rb') as f:
                old_content = zlib.decompress(f.read()).decode('utf-8', errors='replace')
        else:
            old_content = ""
        
        if new_hash:
            new_blob_path = os.path.join('.pvcs', 'objects', new_hash)
            with open(new_blob_path, 'rb') as f:
                new_content = zlib.decompress(f.read()).decode('utf-8', errors='replace')
        else:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                new_content = f.read()
        
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        max_lines = max(len(old_lines), len(new_lines))
        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None
            
            if old_line != new_line:
                if old_line is not None and new_line is None:
                    print(f"- {old_line}")
                elif old_line is None and new_line is not None:
                    print(f"+ {new_line}")
                elif old_line != new_line:
                    print(f"- {old_line}")
                    print(f"+ {new_line}")
    
    except Exception as e:
        print(f"Could not show detailed diff: {e}")

def diff_detailed(commit1=None, commit2=None):
    if commit1 is None and commit2 is None:
        head_hash = load_head()
        old_files = get_commit_files(head_hash) if head_hash else {}
        new_files = get_working_directory_state()
        from_desc, to_desc = "HEAD", "working directory"
    elif commit2 is None:
        commit_hash = resolve_commit_reference(commit1)
        if not commit_hash:
            return
        old_files = get_commit_files(commit_hash)
        new_files = get_working_directory_state()
        from_desc, to_desc = f"commit {commit_hash[:8]}", "working directory"
    else:
        hash1 = resolve_commit_reference(commit1)
        hash2 = resolve_commit_reference(commit2)
        if not hash1 or not hash2:
            return
        old_files = get_commit_files(hash1)
        new_files = get_commit_files(hash2)
        from_desc, to_desc = f"commit {hash1[:8]}", f"commit {hash2[:8]}"
    
    added, removed, modified = compare_file_states(old_files, new_files)
    print_diff_summary(added, removed, modified, from_desc, to_desc)
    
    for file_path in modified:
        old_hash = old_files.get(file_path)
        new_hash = new_files.get(file_path)
        show_file_diff(file_path, old_hash, new_hash)