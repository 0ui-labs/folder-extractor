"""
Unit tests for core/ai_prompts.py module.

Tests cover:
- Prompt generation with various category lists
- JSON schema specification
- Fallback category handling
- Edge cases (empty list, special characters, many categories)

This module follows TDD principles - tests were written before implementation.
"""

from __future__ import annotations

from folder_extractor.core.ai_prompts import get_system_prompt


class TestGetSystemPrompt:
    """Tests for get_system_prompt function."""

    def test_prompt_contains_all_categories(self):
        """Prompt includes all provided categories for document classification."""
        categories = ["Finanzen", "Verträge", "Medizin"]
        prompt = get_system_prompt(categories)

        for category in categories:
            assert category in prompt, f"Category '{category}' should be in prompt"

    def test_prompt_contains_json_schema(self):
        """Prompt specifies the required JSON response format with all fields."""
        categories = ["Finanzen", "Verträge"]
        prompt = get_system_prompt(categories)

        # Check that the JSON schema fields are mentioned
        assert "category" in prompt, "Prompt should mention 'category' field"
        assert "sender" in prompt, "Prompt should mention 'sender' field"
        assert "year" in prompt, "Prompt should mention 'year' field"

        # Check that a JSON example structure is present
        assert "{" in prompt, "Prompt should contain opening brace for JSON example"
        assert "}" in prompt, "Prompt should contain closing brace for JSON example"

    def test_prompt_contains_fallback_category(self):
        """Prompt instructs to use 'Sonstiges' when no category fits."""
        categories = ["Finanzen", "Verträge"]  # Without "Sonstiges"
        prompt = get_system_prompt(categories)

        assert "Sonstiges" in prompt, "Prompt should mention 'Sonstiges' as fallback"

    def test_prompt_with_empty_categories_list(self):
        """Empty category list still produces valid prompt with fallback."""
        prompt = get_system_prompt([])

        # Prompt should still be valid
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # "Sonstiges" should be available as the only category
        assert "Sonstiges" in prompt, (
            "Empty list should still have 'Sonstiges' fallback"
        )

    def test_prompt_with_many_categories(self):
        """Prompt handles large category lists without becoming too long."""
        categories = [
            "Finanzen",
            "Verträge",
            "Medizin",
            "Bildung",
            "Privat",
            "Technik",
            "Arbeit",
            "Reisen",
            "Versicherung",
            "Immobilien",
            "Auto",
            "Haushalt",
            "Sport",
            "Freizeit",
            "Kunst",
            "Musik",
            "Literatur",
            "Familie",
            "Gesundheit",
            "Rechtliches",
            "Steuern",
        ]
        prompt = get_system_prompt(categories)

        # All categories should be present
        for category in categories:
            assert category in prompt, f"Category '{category}' should be in prompt"

        # Prompt should not be excessively long (< 3000 chars for efficiency)
        assert len(prompt) < 3000, "Prompt should stay reasonably sized"

    def test_prompt_with_special_characters_in_categories(self):
        """Prompt correctly handles categories with umlauts and special chars."""
        categories = [
            "Finanzen & Steuern",
            "IT-Technik",
            "Privat/Persönlich",
            "Müller-Dokumente",
        ]
        prompt = get_system_prompt(categories)

        # No exception should occur, and categories should be present
        for category in categories:
            assert category in prompt, f"Category '{category}' should be in prompt"

    def test_prompt_is_string(self):
        """get_system_prompt returns a string type."""
        categories = ["Finanzen", "Verträge"]
        result = get_system_prompt(categories)

        assert isinstance(result, str), "Prompt should be a string"

    def test_prompt_is_not_empty(self):
        """Prompt contains substantial content, not just whitespace."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        assert len(prompt) > 0, "Prompt should not be empty"
        assert prompt.strip() != "", "Prompt should not be only whitespace"
        # A good prompt should have at least 100 characters of instructions
        assert len(prompt.strip()) >= 100, "Prompt should have substantial content"


class TestPromptQuality:
    """Tests for prompt quality and content requirements."""

    def test_prompt_is_in_german(self):
        """Prompt uses German language consistent with UI."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Check for common German words that should appear in instructions
        german_indicators = [
            "Du",  # German "You" (formal/informal)
            "Dokument",  # Document
            "Kategorie",  # Category
        ]

        matches = sum(1 for word in german_indicators if word in prompt)
        assert matches >= 2, "Prompt should be in German"

    def test_prompt_instructs_json_output(self):
        """Prompt clearly instructs the model to output JSON format."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should mention JSON explicitly
        assert "JSON" in prompt or "json" in prompt, "Prompt should mention JSON format"

    def test_prompt_explains_null_handling(self):
        """Prompt explains what to do when information is missing."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should mention null or None for missing values
        assert (
            "null" in prompt.lower()
            or "none" in prompt.lower()
            or "fehlt" in prompt.lower()
        ), "Prompt should explain handling of missing information"

    def test_prompt_mentions_sender_extraction(self):
        """Prompt explains how to extract sender information."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should have some guidance about sender extraction
        sender_terms = ["Absender", "Firma", "sender", "Ersteller"]
        assert any(term in prompt for term in sender_terms), (
            "Prompt should explain sender extraction"
        )

    def test_prompt_mentions_year_extraction(self):
        """Prompt explains how to extract year information."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should have some guidance about year extraction
        year_terms = ["Jahr", "year", "Datum", "2024", "4-stellig"]
        assert any(term in prompt for term in year_terms), (
            "Prompt should explain year extraction"
        )


class TestEntityExtractionPrompt:
    """Tests for Named Entity Recognition prompt features."""

    def test_prompt_contains_entities_field(self):
        """Prompt specifies the entities field for NER output."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        assert "entities" in prompt, "Prompt should mention 'entities' field"

    def test_prompt_specifies_entity_types(self):
        """Prompt defines valid entity types for classification."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        expected_types = ["Organization", "Person", "Project", "Location", "Product"]

        for entity_type in expected_types:
            assert entity_type in prompt, f"Prompt should mention '{entity_type}' type"

    def test_prompt_shows_entities_json_structure(self):
        """Prompt demonstrates entities array structure in JSON example."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should show entity structure with name and type
        assert '"name"' in prompt, "Prompt should show 'name' field in entity"
        assert '"type"' in prompt, "Prompt should show 'type' field in entity"

    def test_prompt_shows_empty_entities_example(self):
        """Prompt shows how to return empty entities list."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should show empty list syntax for no entities case
        assert "[]" in prompt, "Prompt should show empty list syntax for no entities"

    def test_prompt_limits_entity_count(self):
        """Prompt specifies maximum number of entities per document."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should mention limit (5 entities max per plan)
        assert "5" in prompt or "fünf" in prompt.lower(), (
            "Prompt should mention entity count limit"
        )

    def test_prompt_entity_examples_are_realistic(self):
        """Prompt provides realistic entity examples."""
        categories = ["Finanzen"]
        prompt = get_system_prompt(categories)

        # Should have realistic organization example
        assert "Telekom" in prompt or "GmbH" in prompt, (
            "Prompt should show realistic organization example"
        )
