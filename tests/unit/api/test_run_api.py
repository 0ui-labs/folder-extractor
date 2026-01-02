"""
Tests for run_api.py - API Server Entry Point.

These tests verify the behavior of the API server entry point:
- Argument parsing and defaults
- Environment variable loading and fallbacks
- CLI arguments override environment variables
- Error handling for missing dependencies
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class TestArgumentParser:
    """Test suite for CLI argument parsing behavior."""

    def test_default_values_when_no_arguments_provided(self) -> None:
        """CLI provides sensible defaults when no arguments are given."""
        # Import must be inside test to allow mocking
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args([])

        assert args.host == "127.0.0.1"
        assert args.port == 23456
        assert args.reload is False
        assert args.log_level == "info"
        assert args.workers == 1

    def test_custom_port_via_argument(self) -> None:
        """Port can be specified via --port argument."""
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args(["--port", "8000"])

        assert args.port == 8000

    def test_custom_host_via_argument(self) -> None:
        """Host can be specified via --host argument."""
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args(["--host", "0.0.0.0"])

        assert args.host == "0.0.0.0"

    def test_reload_flag_enables_development_mode(self) -> None:
        """--reload flag enables hot-reloading for development."""
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args(["--reload"])

        assert args.reload is True

    def test_log_level_choices_are_valid(self) -> None:
        """Only valid log levels are accepted."""
        from run_api import create_parser

        parser = create_parser()

        valid_levels = ["critical", "error", "warning", "info", "debug"]
        for level in valid_levels:
            args = parser.parse_args(["--log-level", level])
            assert args.log_level == level

    def test_invalid_log_level_raises_error(self) -> None:
        """Invalid log level is rejected by the parser."""
        from run_api import create_parser

        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "invalid"])

    def test_workers_count_can_be_specified(self) -> None:
        """Worker count for production can be specified."""
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args(["--workers", "4"])

        assert args.workers == 4

    def test_multiple_arguments_combined(self) -> None:
        """Multiple arguments can be combined in a single call."""
        from run_api import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
                "--log-level",
                "debug",
                "--workers",
                "2",
                "--reload",
            ]
        )

        assert args.host == "0.0.0.0"
        assert args.port == 9000
        assert args.log_level == "debug"
        assert args.workers == 2
        assert args.reload is True


class TestEnvironmentVariableConfiguration:
    """Test suite for environment variable configuration."""

    def test_env_variables_provide_defaults_when_no_cli_args(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables are used when CLI args are not provided."""
        monkeypatch.setenv("API_HOST", "192.168.1.1")
        monkeypatch.setenv("API_PORT", "5000")
        monkeypatch.setenv("API_LOG_LEVEL", "debug")

        from run_api import get_config

        config = get_config([])

        assert config["host"] == "192.168.1.1"
        assert config["port"] == 5000
        assert config["log_level"] == "debug"

    def test_cli_arguments_override_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI arguments take precedence over environment variables."""
        monkeypatch.setenv("API_HOST", "192.168.1.1")
        monkeypatch.setenv("API_PORT", "5000")

        from run_api import get_config

        config = get_config(["--host", "127.0.0.1", "--port", "8080"])

        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080

    def test_partial_cli_overrides_work_correctly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI args override only the specified values, ENV provides the rest."""
        monkeypatch.setenv("API_HOST", "10.0.0.1")
        monkeypatch.setenv("API_PORT", "3000")
        monkeypatch.setenv("API_LOG_LEVEL", "warning")

        from run_api import get_config

        # Only override port via CLI
        config = get_config(["--port", "8000"])

        assert config["host"] == "10.0.0.1"  # from ENV
        assert config["port"] == 8000  # from CLI (overridden)
        assert config["log_level"] == "warning"  # from ENV

    def test_defaults_used_when_no_env_and_no_cli(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Built-in defaults are used when neither ENV nor CLI provide values."""
        # Ensure ENV vars are not set
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import get_config

        config = get_config([])

        assert config["host"] == "127.0.0.1"
        assert config["port"] == 23456
        assert config["log_level"] == "info"


class TestServerStartup:
    """Test suite for server startup behavior."""

    def test_startup_message_includes_host_and_port(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Startup prints informative message with server address."""
        # Mock uvicorn.run to prevent actual server start
        mock_run = MagicMock()
        monkeypatch.setattr("uvicorn.run", mock_run)

        from run_api import print_startup_message

        print_startup_message("127.0.0.1", 23456)

        captured = capsys.readouterr()
        assert "127.0.0.1" in captured.out
        assert "23456" in captured.out
        assert "http://" in captured.out

    def test_startup_message_includes_docs_url(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Startup message includes link to API documentation."""
        mock_run = MagicMock()
        monkeypatch.setattr("uvicorn.run", mock_run)

        from run_api import print_startup_message

        print_startup_message("localhost", 8000)

        captured = capsys.readouterr()
        assert "/docs" in captured.out

    def test_main_passes_cli_args_to_uvicorn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI arguments passed to main() are correctly forwarded to Uvicorn."""
        # Track the uvicorn.run call arguments
        captured_config: dict[str, Any] = {}

        def mock_run(**kwargs: Any) -> None:
            captured_config.update(kwargs)

        monkeypatch.setattr("uvicorn.run", mock_run)
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import main

        # Call main with explicit CLI args
        exit_code = main(
            ["--port", "8000", "--host", "0.0.0.0", "--log-level", "debug"]
        )

        # Verify the values were passed to uvicorn
        assert exit_code == 0
        assert captured_config["port"] == 8000
        assert captured_config["host"] == "0.0.0.0"
        assert captured_config["log_level"] == "debug"


class TestErrorHandling:
    """Test suite for error handling in the entry point."""

    def test_keyboard_interrupt_prints_graceful_message(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """KeyboardInterrupt (Ctrl+C) prints a graceful shutdown message."""

        # Mock uvicorn.run to raise KeyboardInterrupt
        def mock_run(*args: Any, **kwargs: Any) -> None:
            raise KeyboardInterrupt()

        monkeypatch.setattr("uvicorn.run", mock_run)
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import main

        # Should not raise, but exit gracefully
        exit_code = main([])

        captured = capsys.readouterr()
        assert "stopped" in captured.out.lower() or "beendet" in captured.out.lower()
        assert exit_code == 0

    def test_import_error_provides_helpful_message(self) -> None:
        """ImportError for missing API module provides helpful error message."""
        from run_api import format_import_error_message

        message = format_import_error_message("folder_extractor.api.server")

        # Verify the error message contains helpful information
        assert "api" in message.lower()
        assert "dependencies" in message.lower() or "module" in message.lower()
        assert "pip install" in message.lower()


class TestUvicornConfiguration:
    """Test suite for Uvicorn configuration generation."""

    def test_uvicorn_config_includes_app_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Uvicorn config uses correct app path for import."""
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import get_uvicorn_config

        config = get_uvicorn_config(
            host="127.0.0.1",
            port=23456,
            reload=False,
            log_level="info",
            workers=1,
        )

        assert config["app"] == "folder_extractor.api.server:app"

    def test_workers_only_set_when_reload_is_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Workers count is only applied when not in reload mode."""
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import get_uvicorn_config

        # With reload=True, workers should not be in config
        config_reload = get_uvicorn_config(
            host="127.0.0.1",
            port=23456,
            reload=True,
            log_level="info",
            workers=4,
        )
        assert "workers" not in config_reload

        # With reload=False, workers should be set
        config_no_reload = get_uvicorn_config(
            host="127.0.0.1",
            port=23456,
            reload=False,
            log_level="info",
            workers=4,
        )
        assert config_no_reload["workers"] == 4

    def test_uvicorn_config_enables_access_log(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Access logging is enabled for request tracking."""
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        monkeypatch.delenv("API_LOG_LEVEL", raising=False)

        from run_api import get_uvicorn_config

        config = get_uvicorn_config(
            host="127.0.0.1",
            port=23456,
            reload=False,
            log_level="info",
            workers=1,
        )

        assert config["access_log"] is True
