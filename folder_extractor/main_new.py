#!/usr/bin/env python3
"""
Folder Extractor - Neue modulare Version

Dieses Modul dient als Brücke zwischen der alten monolithischen
und der neuen modularen Architektur.
"""
import sys

# Import der neuen CLI-App
from folder_extractor.cli.app import main as cli_main


def main():
    """Haupteinstiegspunkt für Folder Extractor."""
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())