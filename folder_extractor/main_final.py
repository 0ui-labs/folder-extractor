#!/usr/bin/env python3
"""
Folder Extractor - Main entry point.

This module provides the entry point for the modular architecture.
"""
import sys


def main():
    """Main entry point using the new modular architecture."""
    from folder_extractor.cli.app_v2 import main as enhanced_main
    return enhanced_main()


if __name__ == "__main__":
    sys.exit(main())