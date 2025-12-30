"""
Prompt Engineering System für Smart Sorting.

Dieses Modul generiert strukturierte System-Prompts für die Gemini API,
um Dokumente zuverlässig zu kategorisieren und Named Entities zu extrahieren.

Verwendung:
    from folder_extractor.core.ai_prompts import get_system_prompt
    from folder_extractor.config.settings import get_all_categories

    categories = get_all_categories()
    prompt = get_system_prompt(categories)
    # prompt an AsyncGeminiClient übergeben

Integration:
    - Phase 1: Kategorien aus config/constants.py und settings.py
    - Phase 2: Dieses Modul (ai_prompts.py) mit Entity-Extraktion
    - Phase 3: SmartSorter verwendet diesen Prompt für Dokumenten-Analyse
"""

from __future__ import annotations


def get_system_prompt(categories: list[str]) -> str:
    """
    Generiert System-Prompt für Dokumenten-Kategorisierung mit Entity-Extraktion.

    Der Prompt instruiert die Gemini API, Dokumente zu analysieren und
    strukturierte JSON-Antworten mit Kategorie, Absender, Jahr und
    Named Entities zurückzugeben.

    Args:
        categories: Liste der erlaubten Kategorien.
            Kann leer sein - "Sonstiges" wird immer als Fallback verwendet.

    Returns:
        Vollständiger System-Prompt als String, bereit für die API.

    Examples:
        >>> prompt = get_system_prompt(["Finanzen", "Verträge"])
        >>> "Finanzen" in prompt
        True
        >>> "Sonstiges" in prompt  # Fallback immer verfügbar
        True
        >>> "entities" in prompt  # Entity-Extraktion
        True
    """
    # Kategorien als formatierte Liste vorbereiten
    if categories:
        categories_str = ", ".join(categories)
        categories_section = f"Verfügbare Kategorien: {categories_str}"
    else:
        categories_section = "Keine benutzerdefinierten Kategorien verfügbar."

    prompt = f"""Du bist ein Experte für Dokumenten-Kategorisierung und Named Entity Recognition.

## Deine Aufgabe

Analysiere das bereitgestellte Dokument und extrahiere folgende Informationen:
1. **Kategorie**: Die passendste Kategorie aus der vorgegebenen Liste
2. **Absender**: Der Firmenname oder die Person, die das Dokument erstellt hat
3. **Jahr**: Das Jahr aus dem Dokumentdatum (4-stellig, z.B. 2024)
4. **Entities**: Liste von Organisationen, Personen oder wichtigen Begriffen im Dokument

## {categories_section}

Falls keine Kategorie passt, wähle "Sonstiges".

## Antwortformat

Antworte ausschließlich im folgenden JSON-Format:

```json
{{
  "category": "Kategoriename",
  "sender": "Absendername",
  "year": "2024",
  "entities": [
    {{"name": "Beispiel GmbH", "type": "Organization"}},
    {{"name": "Projekt X", "type": "Project"}}
  ]
}}
```

## Regeln

- **category**: Muss eine Kategorie aus der Liste oder "Sonstiges" sein (String)
- **sender**: Firmenname, Behörde oder Personenname. Null wenn nicht erkennbar.
- **year**: Vierstellige Jahreszahl (z.B. "2024"). Null wenn kein Datum vorhanden.
- **entities**: Liste von Dictionaries mit "name" und "type".
  - Typen: "Organization" (Firmen, Behörden), "Person" (Namen), "Project" (Projektnamen), "Location" (Orte), "Product" (Produkte)
  - Leere Liste [] wenn keine Entities erkennbar
  - Maximal 5 wichtigste Entities pro Dokument

## Beispiele

Rechnung von "Telekom Deutschland GmbH" vom 15.03.2024:
```json
{{
  "category": "Finanzen",
  "sender": "Telekom Deutschland GmbH",
  "year": "2024",
  "entities": [
    {{"name": "Telekom Deutschland GmbH", "type": "Organization"}},
    {{"name": "MagentaZuhause", "type": "Product"}}
  ]
}}
```

Persönliches Foto ohne erkennbaren Absender:
```json
{{
  "category": "Privat",
  "sender": null,
  "year": null,
  "entities": []
}}
```

Antworte nur mit dem JSON-Objekt, ohne zusätzlichen Text."""

    return prompt
