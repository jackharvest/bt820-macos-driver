"""Frozen-bundle entry point.

PyInstaller runs the target script as __main__, which breaks the package's
relative imports, so freeze this shim instead of src/bt820/cli.py.
"""
import sys

from bt820.cli import main

if __name__ == "__main__":
    sys.exit(main())
