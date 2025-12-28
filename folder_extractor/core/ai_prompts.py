"""
Prompt Engineering System für Smart Sorting.

Dieses Modul generiert strukturierte System-Prompts für die Gemini API,
um Dokumente zuverlässig zu kategorisieren.

Verwendung:
    from folder_extractor.core.ai_prompts import get_system_prompt
    from folder_extractor.config.settings import get_all_categories

    categories = get_all_categories()
    prompt = get_system_prompt(categories)
    # prompt an AsyncGeminiClient übergeben

Integration:
    - Phase 1: Kategorien aus config/constants.py und settings.py
    - Phase 2: Dieses Modul (ai_prompts.py)
    - Phase 3: SmartSorter verwendet diesen Prompt für Dokumenten-Analyse
"""

from __future__ import annotations


def get_system_prompt(categories: list[str]) -> str:
    """
    Generiert System-Prompt für Dokumenten-Kategorisierung.

    Der Prompt instruiert die Gemini API, Dokumente zu analysieren und
    strukturierte JSON-Antworten mit Kategorie, Absender und Jahr
    zurückzugeben.

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
    """
    # Kategorien als formatierte Liste vorbereiten
    if categories:
        categories_str = ", ".join(categories)
        categories_section = f"Verfügbare Kategorien: {categories_str}"
    else:
        categories_section = "Keine benutzerdefinierten Kategorien verfügbar."

    prompt = f"""Du bist ein Experte für Dokumenten-Kategorisierung.

## Deine Aufgabe

Analysiere das bereitgestellte Dokument und extrahiere folgende Informationen:
1. **Kategorie**: Die passendste Kategorie aus der vorgegebenen Liste
2. **Absender**: Der Firmenname oder die Person, die das Dokument erstellt hat
3. **Jahr**: Das Jahr aus dem Dokumentdatum (4-stellig, z.B. 2024)

## {categories_section}

Falls keine Kategorie passt, wähle "Sonstiges".

## Antwortformat

Antworte ausschließlich im folgenden JSON-Format:

```json
{{"category": "Kategoriename", "sender": "Absendername", "year": "2024"}}
```

## Regeln

- **category**: Muss eine Kategorie aus der Liste oder "Sonstiges" sein (String)
- **sender**: Firmenname, Behörde oder Personenname. Null wenn nicht erkennbar.
- **year**: Vierstellige Jahreszahl (z.B. "2024"). Null wenn kein Datum vorhanden.

## Beispiele

Rechnung von "Telekom Deutschland GmbH" vom 15.03.2024:
```json
{{"category": "Finanzen", "sender": "Telekom Deutschland GmbH", "year": "2024"}}
```

Persönliches Foto ohne erkennbaren Absender:
```json
{{"category": "Privat", "sender": null, "year": null}}
```

Antworte nur mit dem JSON-Objekt, ohne zusätzlichen Text."""

    return prompt
