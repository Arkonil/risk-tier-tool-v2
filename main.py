import argparse
import sys

from risc_tool import run_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        print("-" * 100)
        print("Running in debugger mode")
        print("-" * 100)

    run_app(args.debug)
