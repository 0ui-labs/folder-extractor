I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Beobachtungen

Das Projekt `folder_extractor` verwendet aktuell keine Linter oder Formatter. Die `file:requirements.txt` enthält nur Test- und Build-Tools (pytest, coverage, twine, rich). Die `file:setup.py` definiert Python 3.8+ als Mindestversion. Die `file:pyproject.toml` enthält nur Coverage- und Pytest-Konfigurationen. Es gibt keine Legacy-Tools (Black, Flake8, Isort) zu entfernen, was die Integration von Ruff vereinfacht.

## Ansatz

Ruff wird als zentrale Lösung für Linting und Formatting integriert. Die Konfiguration erfolgt ausschließlich in `file:pyproject.toml` mit drei Sektionen: `[tool.ruff]` für globale Einstellungen, `[tool.ruff.lint]` für Linting-Regeln und `[tool.ruff.format]` für Formatting-Optionen. Die Regel-Sets E, F, I, B, UP und SIM werden aktiviert, um Fehler zu erkennen, Importe zu sortieren, Bugs zu finden und Code zu modernisieren. Die Konfiguration folgt den Black-Standards (Line Length 88) und zielt auf Python 3.8 Kompatibilität ab.

## Implementierungsschritte

### 1. Dependency in requirements.txt hinzufügen

Öffne `file:requirements.txt` und füge `ruff>=0.3.0` im Development-Bereich hinzu (nach Zeile 1, vor pytest):

```
# Development requirements
ruff>=0.3.0
pytest>=8.0.0
```

**Begründung**: Ruff wird als Development-Tool benötigt, nicht als Runtime-Dependency.

---

### 2. Ruff-Konfiguration in pyproject.toml erstellen

Öffne `file:pyproject.toml` und füge am Ende der Datei (nach der pytest-Konfiguration) folgende drei Sektionen hinzu:

#### 2.1 Globale Ruff-Einstellungen

```toml
[tool.ruff]
# Line length matching Black's default
line-length = 88

# Target Python 3.8 for compatibility
target-version = "py38"

# Exclude common directories
exclude = [
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "venv",
    ".venv",
]
```

**Konfigurationsdetails**:
- `line-length = 88`: Standard von Black, konsistent mit modernen Python-Projekten
- `target-version = "py38"`: Entspricht der Mindestversion in `file:setup.py` (Zeile 38)
- `exclude`: Verhindert Linting von generierten/temporären Dateien

#### 2.2 Linting-Regeln konfigurieren

```toml
[tool.ruff.lint]
# Enable rule sets as requested
select = [
    "E",    # pycodestyle errors
    "F",    # Pyflakes
    "I",    # isort (import sorting)
    "B",    # flake8-bugbear (subtle bugs)
    "UP",   # pyupgrade (modernize syntax)
    "SIM",  # flake8-simplify (code simplification)
]

# Start with no ignores - be strict
ignore = []

# Allow auto-fixing for all enabled rules
fixable = ["ALL"]
unfixable = []

# Per-file ignores for common patterns
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__.py
"tests/**/*.py" = ["S101"]  # Allow assert statements in tests
```

**Regel-Set Erklärung**:
- **E, F**: Basis-Fehler und Code-Qualität (Pyflakes, pycodestyle)
- **I**: Import-Sortierung (ersetzt Isort)
- **B**: Erkennt subtile Bugs (z.B. mutable default arguments)
- **UP**: Modernisiert Syntax (z.B. `typing.List` → `list`)
- **SIM**: Vereinfacht Code (z.B. `if x == True:` → `if x:`)

**Per-File-Ignores**:
- `F401` in `__init__.py`: Erlaubt Re-Exports ohne "unused import" Warnung
- `S101` in Tests: Erlaubt `assert`-Statements (Standard in pytest)

#### 2.3 Formatter-Einstellungen

```toml
[tool.ruff.format]
# Use double quotes (Black-compatible)
quote-style = "double"

# Use spaces for indentation
indent-style = "space"

# Respect magic trailing commas
skip-magic-trailing-comma = false

# Auto-detect line endings
line-ending = "auto"
```

**Formatter-Details**:
- `quote-style = "double"`: Konsistent mit Black (bevorzugt `"string"` über `'string'`)
- `indent-style = "space"`: 4 Spaces pro Indentation-Level (Python-Standard)
- `skip-magic-trailing-comma = false`: Respektiert trailing commas für bessere Diffs
- `line-ending = "auto"`: Plattform-agnostisch (LF auf Unix, CRLF auf Windows)

---

### 3. Verifikation der Konfiguration

Nach dem Hinzufügen der Konfiguration sollte die Struktur von `file:pyproject.toml` wie folgt aussehen:

```
[tool.coverage.run]
...

[tool.coverage.report]
...

[tool.pytest.ini_options]
...

[tool.ruff]
...

[tool.ruff.lint]
...

[tool.ruff.format]
...
```

**Wichtig**: Die Ruff-Sektionen müssen nach den bestehenden Tool-Konfigurationen stehen, um die Lesbarkeit zu gewährleisten.

---

## Zusammenfassung der Änderungen

| Datei | Änderung | Zeilen |
|-------|----------|--------|
| `file:requirements.txt` | `ruff>=0.3.0` hinzufügen | Nach Zeile 1 |
| `file:pyproject.toml` | `[tool.ruff]` Sektion | Nach Zeile 44 |
| `file:pyproject.toml` | `[tool.ruff.lint]` Sektion | Nach `[tool.ruff]` |
| `file:pyproject.toml` | `[tool.ruff.format]` Sektion | Nach `[tool.ruff.lint]` |

---

## Erwartetes Ergebnis

Nach dieser Phase:
- ✅ Ruff ist als Dependency verfügbar
- ✅ Zentrale Konfiguration in `file:pyproject.toml` vorhanden
- ✅ Strikte Linting-Regeln (E, F, I, B, UP, SIM) aktiviert
- ✅ Black-kompatible Formatting-Einstellungen konfiguriert
- ✅ Python 3.8 Kompatibilität gewährleistet
- ✅ Keine Legacy-Tools zu entfernen (sauberer Start)

Die Konfiguration ist bereit für die nächste Phase (Anwendung von `ruff check --fix` und `ruff format`).