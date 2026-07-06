"""Legacy entrypoint for backward compatibility. Use cli.py instead of main.py."""

import sys

from cli import launch

if __name__ == "__main__":
    print("WARNING: main.py is deprecated. Use cli.py instead.", file=sys.stderr)
    launch()
