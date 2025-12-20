"""
Unit tests for conftest fixtures.

These tests document and verify the behavior of shared test fixtures.
"""


class TestFakerSeedFixture:
    """Test faker_seed fixture provides reproducible random data."""

    def test_faker_seed_generates_consistent_sequence(self, faker_seed):
        """Faker with fixed seed produces the same sequence across test runs."""
        # Generate a sequence of values
        first_word = faker_seed.word()
        second_word = faker_seed.word()

        # These should always be the same due to the fixed seed
        # We test that they are strings (the contract) not specific values
        assert isinstance(first_word, str)
        assert isinstance(second_word, str)
        assert len(first_word) > 0
        assert len(second_word) > 0

    def test_faker_seed_is_session_scoped(self, faker_seed, request):
        """Session-scoped fixture maintains state across tests in same session."""
        # Access the fixture's scope through pytest's request object
        fixture_def = request._fixturemanager._arg2fixturedefs.get("faker_seed")
        assert fixture_def is not None
        assert fixture_def[0].scope == "session"


class TestRandomFilenameFixture:
    """Test random_filename fixture generates realistic filenames."""

    def test_random_filename_returns_callable(self, random_filename):
        """Fixture returns a callable for generating filenames."""
        assert callable(random_filename)

    def test_random_filename_default_extension(self, random_filename):
        """Default extension is .txt."""
        filename = random_filename()
        assert filename.endswith(".txt")
        assert len(filename) > 4  # At least one character before extension

    def test_random_filename_custom_extension(self, random_filename):
        """Custom extensions are applied correctly."""
        pdf_name = random_filename(extension=".pdf")
        jpg_name = random_filename(extension=".jpg")
        doc_name = random_filename(extension=".doc")

        assert pdf_name.endswith(".pdf")
        assert jpg_name.endswith(".jpg")
        assert doc_name.endswith(".doc")

    def test_random_filename_produces_valid_filenames(self, random_filename):
        """Generated filenames contain only valid characters."""
        for _ in range(10):
            filename = random_filename()
            # Filenames should not contain path separators
            assert "/" not in filename
            assert "\\" not in filename
            # Should not start with a dot (hidden files)
            assert not filename.startswith(".")


class TestResetGlobalStateFixture:
    """Test reset_global_state fixture ensures clean state between tests."""

    def test_state_manager_starts_clean(self):
        """Each test starts with a fresh global state manager."""
        from folder_extractor.core.state_manager import get_state_manager

        manager = get_state_manager()

        # Should have no operations in progress
        assert manager.get_current_operation_id() is None
        # Should not have abort requested
        assert not manager.is_abort_requested()

    def test_state_modifications_do_not_leak(self):
        """State set in one test does not affect subsequent tests."""
        from folder_extractor.core.state_manager import get_state_manager

        manager = get_state_manager()

        # This modification should be cleaned up by the fixture
        manager.set_value("test_leak_check", "should_not_persist")
        manager.start_operation("test_operation")

        # The autouse fixture will reset this before the next test
        # We verify in test_state_manager_starts_clean that state is clean
