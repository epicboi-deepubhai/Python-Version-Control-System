import re

def load_ignore_patterns():
    patterns = ['.pvcsignore', '.git', '.pvcs']
    try:
        with open('.pvcsignore', 'r') as f:
            for line in f:
                patterns.extend(line.split())
    except FileNotFoundError:
        pass
    return patterns

def is_ignored(path, patterns):
    return any(re.search(re.escape(pattern), path) for pattern in patterns)
