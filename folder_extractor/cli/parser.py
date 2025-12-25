"""
Command line argument parser.

Handles parsing and validation of CLI arguments.
"""

import argparse
import sys
from typing import List, Optional

from folder_extractor.config.constants import AUTHOR, HELP_TEXT, VERSION
from folder_extractor.utils.parsers import parse_depth


class ArgumentParser:
    """Custom argument parser for Folder Extractor."""

    def __init__(self):
        """Initialize argument parser."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            prog="folder-extractor",
            description="Dateien aus Unterordnern extrahieren",
            add_help=False,  # We'll handle help ourselves
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Add arguments
        parser.add_argument(
            "-h", "--help", action="store_true", help="Diese Hilfe anzeigen"
        )

        parser.add_argument(
            "-v", "--version", action="store_true", help="Version anzeigen"
        )

        parser.add_argument(
            "-d",
            "--depth",
            type=str,
            default="0",
            metavar="TIEFE",
            help="Maximale Ordnertiefe (0 = unbegrenzt)",
        )

        parser.add_argument(
            "-t",
            "--type",
            type=str,
            metavar="TYPEN",
            help="Nur bestimmte Dateitypen (z.B. pdf,jpg,mp3)",
        )

        parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help="Testlauf - zeigt was passieren würde",
        )

        parser.add_argument(
            "-s",
            "--sort-by-type",
            action="store_true",
            help="Dateien nach Typ in Unterordner sortieren",
        )

        parser.add_argument(
            "-u",
            "--undo",
            action="store_true",
            help="Letzte Operation rückgängig machen",
        )

        parser.add_argument(
            "--include-hidden",
            action="store_true",
            help="Versteckte Dateien einbeziehen",
        )

        parser.add_argument(
            "--deduplicate",
            action="store_true",
            help="Identische Dateien (gleicher Inhalt) nicht duplizieren",
        )

        parser.add_argument(
            "--smart-merge",
            action="store_true",
            dest="deduplicate",
            help="Alias für --deduplicate",
        )

        parser.add_argument(
            "--domain",
            type=str,
            metavar="DOMAINS",
            help="Nur Weblinks von bestimmten Domains (z.B. youtube.com)",
        )

        parser.add_argument(
            "--global-dedup",
            action="store_true",
            help="Globale Deduplizierung (kann bei großen Ordnern langsam sein)",
        )

        parser.add_argument(
            "--extract-archives",
            action="store_true",
            help="Archive (ZIP, TAR, GZ) entpacken und Inhalt extrahieren",
        )

        parser.add_argument(
            "--delete-archives",
            action="store_true",
            help="Original-Archive nach erfolgreichem Entpacken löschen (nur mit --extract-archives)",
        )

        return parser

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command line arguments.

        Args:
            args: Optional list of arguments (for testing)

        Returns:
            Parsed arguments namespace
        """
        # Parse arguments
        parsed = self.parser.parse_args(args)

        # Handle special cases
        if parsed.help:
            self.print_help()
            sys.exit(0)

        if parsed.version:
            self.print_version()
            sys.exit(0)

        # Validate and convert depth
        try:
            parsed.depth = parse_depth(parsed.depth)
        except ValueError as e:
            self.parser.error(str(e))

        return parsed

    def print_help(self) -> None:
        """Print custom help text."""
        print(HELP_TEXT)

    def print_version(self) -> None:
        """Print version information."""
        print(f"folder-extractor {VERSION}")
        print(f"Von {AUTHOR}")


def create_parser() -> ArgumentParser:
    """Create and return a configured argument parser."""
    return ArgumentParser()
