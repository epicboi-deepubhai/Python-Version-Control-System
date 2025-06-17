import sys
from pvcs.commands import init, take_snapshot, revert
from pvcs.core import log
from pvcs.diff import diff, diff_detailed

def run():
    args = sys.argv[1:]
    if not args:
        print("No command provided.")
        return

    command = args[0]

    if command == "init":
        init()
    elif command == "snapshot":
        msg = None
        if "-m" in args:
            idx = args.index("-m")
            try:
                msg = args[idx + 1]
            except IndexError:
                print("Missing message after -m")
                return
        take_snapshot(msg)
    elif command == "revert":
        if "-m" in args:
            try:
                idx = args.index("-m")
                revert(args[idx + 1], is_message=True)
            except IndexError:
                print("Missing message after -m")
        elif len(args) > 1:
            revert(args[1])
        else:
            print("Missing snapshot hash or -m flag")
    elif command == "log":
        n = 10
        if "-n" in args:
            try:
                idx = args.index("-n")
                n = int(args[idx + 1])
            except (IndexError, ValueError):
                print("Usage: pvcs.py log -n <number>")
                return
        log(n)
    elif command == 'diff':
        args.extend((None, None))
        f1, f2 = args[1:3] 
        diff(f1, f2)
    else:
        print("Unknown command.")

