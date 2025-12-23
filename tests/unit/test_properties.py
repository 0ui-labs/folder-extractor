"""
Property-Based Tests für die generate_unique_name Funktion.

Diese Tests verwenden Hypothesis, um automatisch eine Vielzahl von Testfällen
zu generieren und die Invarianten der Funktion zu verifizieren.
"""

import re
import string
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from folder_extractor.main import generiere_eindeutigen_namen

# =============================================================================
# Hypothesis-Strategien für Dateinamen
# =============================================================================

# Strategien für realistische Dateinamen
SAFE_FILENAME_CHARS = string.ascii_letters + string.digits + "_-"
COMMON_EXTENSIONS = [".txt", ".pdf", ".jpg", ".png", ".doc", ".tar.gz", ""]

# Strategie für Basisnamen (ohne problematische Zeichen für Dateisysteme)
safe_basename = st.text(
    alphabet=SAFE_FILENAME_CHARS,
    min_size=1,
    max_size=30,
).filter(lambda x: x.strip() != "" and not x.startswith("."))

# Strategie für Dateiendungen
extension = st.sampled_from(COMMON_EXTENSIONS)


class TestGenerateUniqueNameProperties:
    """Property-Based Tests für generiere_eindeutigen_namen."""

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename, ext=extension)
    def test_unique_name_differs_on_conflict(self, basename: str, ext: str):
        """
        Invariante: Bei existierender Datei muss der Output vom Input abweichen.

        Diese Property stellt sicher, dass die Funktion niemals einen Namen
        zurückgibt, der bereits existiert (Konfliktauflösung).
        """
        filename = f"{basename}{ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Erstelle existierende Datei (Konflikt)
            existing_file = Path(temp_dir) / filename
            existing_file.touch()

            # Rufe Funktion auf
            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Output muss sich vom Input unterscheiden
            assert result != filename, (
                f"Bei Konflikt muss sich der Name ändern: "
                f"Input={filename}, Output={result}"
            )

            # Zusätzliche Invariante: Der neue Name darf nicht existieren
            assert not (Path(temp_dir) / result).exists(), (
                f"Der generierte Name existiert bereits: {result}"
            )

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        basename=safe_basename,
        ext=st.sampled_from([".txt", ".pdf", ".jpg", ".png", ".doc"]),
    )
    def test_extension_preserved(self, basename: str, ext: str):
        """
        Invariante: Die Dateiendung muss nach Konfliktauflösung erhalten bleiben.

        Wenn eine Datei "report.pdf" umbenannt wird, muss das Ergebnis
        immer noch auf ".pdf" enden.
        """
        filename = f"{basename}{ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Erstelle Konflikt
            existing_file = Path(temp_dir) / filename
            existing_file.touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Erweiterung muss identisch sein
            original_suffix = Path(filename).suffix
            result_suffix = Path(result).suffix

            assert result_suffix == original_suffix, (
                f"Erweiterung nicht erhalten: "
                f"Original={original_suffix}, Ergebnis={result_suffix}"
            )

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename)
    def test_extension_preserved_no_extension(self, basename: str):
        """
        Invariante: Dateien ohne Erweiterung behalten keine Erweiterung.

        Wenn "README" umbenannt wird, muss das Ergebnis "README_1" sein,
        nicht "README_1.txt" oder ähnlich.
        """
        filename = basename  # Keine Erweiterung

        with tempfile.TemporaryDirectory() as temp_dir:
            existing_file = Path(temp_dir) / filename
            existing_file.touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Keine Erweiterung hinzugefügt
            assert Path(result).suffix == "", (
                f"Unerwartete Erweiterung hinzugefügt: {Path(result).suffix}"
            )

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename, ext=extension)
    def test_generated_name_format(self, basename: str, ext: str):
        """
        Invariante: Generierte Namen folgen dem Format {basename}_{number}{extension}.

        Die Nummer muss eine positive Ganzzahl sein.
        """
        filename = f"{basename}{ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            existing_file = Path(temp_dir) / filename
            existing_file.touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Bei Konflikt muss das Muster _N vor der Erweiterung erscheinen
            # Extrahiere die Nummer
            result_stem = Path(result).stem
            original_stem = Path(filename).stem

            # Der Stem sollte mit dem Original beginnen und _N enden
            assert result_stem.startswith(original_stem), (
                f"Basisname nicht erhalten: Original={original_stem}, "
                f"Ergebnis={result_stem}"
            )

            # Prüfe das _N Suffix
            suffix_part = result_stem[len(original_stem) :]
            pattern = r"^_(\d+)$"
            match = re.match(pattern, suffix_part)

            assert match is not None, (
                f"Ungültiges Namensformat: {result} (erwartet: {original_stem}_N{ext})"
            )

            # Die Nummer muss positiv sein
            number = int(match.group(1))
            assert number >= 1, f"Nummer muss >= 1 sein, war: {number}"

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        basename=safe_basename,
        ext=st.sampled_from([".txt", ".pdf", ".jpg"]),
        num_existing=st.integers(min_value=1, max_value=10),
    )
    def test_multiple_conflicts_increment(
        self, basename: str, ext: str, num_existing: int
    ):
        """
        Invariante: Bei n existierenden Dateien wird die kleinste freie Nummer verwendet.

        Wenn test.txt, test_1.txt, ..., test_{n-1}.txt existieren,
        muss das Ergebnis test_{n}.txt sein (sofern keine Lücken).
        """
        filename = f"{basename}{ext}"
        stem = Path(filename).stem

        with tempfile.TemporaryDirectory() as temp_dir:
            # Erstelle Originaldatei und nummerierte Varianten
            (Path(temp_dir) / filename).touch()
            for i in range(1, num_existing):
                (Path(temp_dir) / f"{stem}_{i}{ext}").touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Ergebnis muss die nächste freie Nummer sein
            expected = f"{stem}_{num_existing}{ext}"
            assert result == expected, (
                f"Bei {num_existing} existierenden Dateien: "
                f"erwartet={expected}, erhalten={result}"
            )

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        basename=safe_basename,
        ext=st.sampled_from([".txt", ".pdf"]),
        gap_position=st.integers(min_value=1, max_value=5),
    )
    def test_finds_gap_in_numbering(self, basename: str, ext: str, gap_position: int):
        """
        Invariante: Die Funktion findet Lücken in der Nummerierung.

        Wenn test.txt, test_1.txt, test_3.txt existieren (Lücke bei _2),
        muss test_2.txt zurückgegeben werden.
        """
        filename = f"{basename}{ext}"
        stem = Path(filename).stem

        with tempfile.TemporaryDirectory() as temp_dir:
            # Erstelle Dateien mit Lücke
            (Path(temp_dir) / filename).touch()
            for i in range(1, gap_position + 3):
                if i != gap_position:  # Lücke an gap_position
                    (Path(temp_dir) / f"{stem}_{i}{ext}").touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Die Lücke wird gefunden
            expected = f"{stem}_{gap_position}{ext}"
            assert result == expected, (
                f"Lücke bei Position {gap_position} nicht gefunden: "
                f"erwartet={expected}, erhalten={result}"
            )

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename, ext=extension)
    def test_no_conflict_returns_original(self, basename: str, ext: str):
        """
        Invariante: Ohne Konflikt wird der Originalname zurückgegeben.

        In einem leeren Verzeichnis muss die Funktion den Input
        unverändert zurückgeben.
        """
        filename = f"{basename}{ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Kein Konflikt - Verzeichnis ist leer
            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Original wird zurückgegeben
            assert result == filename, (
                f"Ohne Konflikt sollte Original zurückgegeben werden: "
                f"Input={filename}, Output={result}"
            )

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename, ext=extension)
    def test_result_is_always_valid_string(self, basename: str, ext: str):
        """
        Invariante: Die Funktion gibt immer einen gültigen, nicht-leeren String zurück.

        Unabhängig vom Input darf die Funktion niemals None oder
        einen leeren String zurückgeben.
        """
        filename = f"{basename}{ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test ohne Konflikt
            result_no_conflict = generiere_eindeutigen_namen(temp_dir, filename)
            assert isinstance(result_no_conflict, str), "Ergebnis muss String sein"
            assert len(result_no_conflict) > 0, "Ergebnis darf nicht leer sein"

            # Test mit Konflikt
            (Path(temp_dir) / filename).touch()
            result_with_conflict = generiere_eindeutigen_namen(temp_dir, filename)
            assert isinstance(result_with_conflict, str), "Ergebnis muss String sein"
            assert len(result_with_conflict) > 0, "Ergebnis darf nicht leer sein"

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(basename=safe_basename, ext=extension)
    def test_result_contains_no_invalid_characters(self, basename: str, ext: str):
        """
        Invariante: Der zurückgegebene Name enthält keine ungültigen Zeichen.

        Ungültige Zeichen sind:
        - Pfad-Trenner (/, \\)
        - Steuerzeichen (ASCII 0-31)
        - Null-Byte

        Der Name darf nur Buchstaben, Ziffern, Unterstriche, Bindestriche,
        Punkte und den Zähler-Delimiter (_) enthalten.
        """
        filename = f"{basename}{ext}"

        # Ungültige Zeichen, die niemals in einem Dateinamen erscheinen dürfen
        FORBIDDEN_CHARS = set("/\\") | {chr(i) for i in range(32)} | {"\x00"}

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test ohne Konflikt
            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Prüfe auf verbotene Zeichen
            forbidden_found = [c for c in result if c in FORBIDDEN_CHARS]
            assert not forbidden_found, (
                f"Ungültige Zeichen im Ergebnis gefunden: {forbidden_found!r} "
                f"in '{result}'"
            )

            # Test mit Konflikt
            (Path(temp_dir) / filename).touch()
            result_with_conflict = generiere_eindeutigen_namen(temp_dir, filename)

            forbidden_found = [c for c in result_with_conflict if c in FORBIDDEN_CHARS]
            assert not forbidden_found, (
                f"Ungültige Zeichen im Ergebnis gefunden: {forbidden_found!r} "
                f"in '{result_with_conflict}'"
            )


class TestGenerateUniqueNameEdgeCases:
    """Edge-Case-Tests für spezielle Dateinamen-Szenarien."""

    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        basename=st.text(
            alphabet=string.ascii_letters + string.digits + " äöüÄÖÜß_-",
            min_size=1,
            max_size=20,
        ).filter(lambda x: x.strip() != "" and not x.startswith("."))
    )
    def test_unicode_and_spaces_handling(self, basename: str):
        """
        Invariante: Dateinamen mit Umlauten und Leerzeichen werden korrekt behandelt.

        Deutsche Umlaute und Leerzeichen sind gültige Zeichen in Dateinamen
        und müssen von der Funktion korrekt verarbeitet werden.
        """
        filename = f"{basename}.txt"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Erstelle Konflikt
            try:
                (Path(temp_dir) / filename).touch()
            except OSError:
                # Manche Zeichen können auf bestimmten Filesystems ungültig sein
                pytest.skip(f"Dateiname nicht erlaubt auf diesem System: {filename}")

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Funktion gibt gültigen String zurück
            assert isinstance(result, str)
            assert len(result) > 0
            # Erweiterung muss erhalten bleiben
            assert result.endswith(".txt")

    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        basename=st.text(
            alphabet=string.ascii_letters,
            min_size=1,
            max_size=10,
        ),
        double_ext=st.sampled_from([".tar.gz", ".tar.bz2", ".tar.xz"]),
    )
    def test_double_extension_handling(self, basename: str, double_ext: str):
        """
        Invariante: Doppelte Erweiterungen werden nach Path.suffix-Semantik behandelt.

        Bei "archive.tar.gz" ist Path.suffix nur ".gz", nicht ".tar.gz".
        Die Funktion muss konsistent mit dieser Semantik arbeiten.
        """
        filename = f"{basename}{double_ext}"

        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / filename).touch()

            result = generiere_eindeutigen_namen(temp_dir, filename)

            # Invariante: Path.suffix-Semantik wird eingehalten
            original_suffix = Path(filename).suffix  # z.B. ".gz"
            result_suffix = Path(result).suffix

            assert result_suffix == original_suffix, (
                f"Suffix-Semantik nicht eingehalten: "
                f"Original suffix={original_suffix}, Result suffix={result_suffix}"
            )
