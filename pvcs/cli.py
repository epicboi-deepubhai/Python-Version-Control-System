import sys
from pvcs.commands import init, take_snapshot, revert

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
    else:
        print("Unknown command.")
