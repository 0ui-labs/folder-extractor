"""
Unit tests for utils/terminal.py module.
"""
import io
import sys
import platform
from unittest.mock import patch, MagicMock
import pytest

from folder_extractor.utils.terminal import (
    save_terminal_settings,
    restore_terminal_settings,
    set_raw_mode,
    clear_line,
    move_cursor_up,
    move_cursor_down,
    get_terminal_width,
    format_progress_bar,
    supports_color,
    Color,
)


class TestSaveTerminalSettings:
    """Tests for save_terminal_settings function."""

    def test_returns_none_on_windows(self):
        """Test that Windows returns None."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
            result = save_terminal_settings()
            assert result is None

    def test_returns_none_when_no_fileno(self):
        """Test returns None when stdin has no fileno."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            del mock_stdin.fileno  # Remove fileno attribute
            with patch.object(sys, 'stdin', mock_stdin):
                result = save_terminal_settings()
                assert result is None

    def test_returns_none_when_not_tty(self):
        """Test returns None when stdin is not a TTY."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = False
            with patch.object(sys, 'stdin', mock_stdin):
                result = save_terminal_settings()
                assert result is None

    def test_returns_settings_on_unix_tty(self):
        """Test returns settings when on Unix with TTY."""
        if platform.system() == 'Windows':
            pytest.skip("Unix-specific test")

        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.return_value = 0
            with patch.object(sys, 'stdin', mock_stdin):
                with patch('folder_extractor.utils.terminal.termios.tcgetattr', return_value=[1, 2, 3]):
                    result = save_terminal_settings()
                    assert result == [1, 2, 3]

    def test_handles_exception(self):
        """Test handles exceptions gracefully."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.side_effect = Exception("Test error")
            with patch.object(sys, 'stdin', mock_stdin):
                result = save_terminal_settings()
                assert result is None


class TestRestoreTerminalSettings:
    """Tests for restore_terminal_settings function."""

    def test_windows_does_not_call_termios(self):
        """On Windows, terminal settings are not modified."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
            with patch('folder_extractor.utils.terminal.termios.tcsetattr') as mock_set:
                restore_terminal_settings([1, 2, 3])
                mock_set.assert_not_called()

    def test_none_settings_does_not_call_termios(self):
        """When settings is None, terminal is not modified."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            with patch('folder_extractor.utils.terminal.termios.tcsetattr') as mock_set:
                restore_terminal_settings(None)
                mock_set.assert_not_called()

    def test_restores_on_unix_tty(self):
        """On Unix with TTY, terminal settings are restored via tcsetattr."""
        if platform.system() == 'Windows':
            pytest.skip("Unix-specific test")

        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.return_value = 0
            with patch.object(sys, 'stdin', mock_stdin):
                with patch('folder_extractor.utils.terminal.termios.tcsetattr') as mock_set:
                    with patch('folder_extractor.utils.terminal.termios.TCSANOW', 0):
                        restore_terminal_settings([1, 2, 3])
                        mock_set.assert_called_once()

    def test_fileno_error_leaves_terminal_unchanged(self):
        """If fileno() raises, terminal state is preserved (no partial restore)."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.side_effect = Exception("Test error")
            with patch.object(sys, 'stdin', mock_stdin):
                with patch('folder_extractor.utils.terminal.termios.tcsetattr') as mock_set:
                    restore_terminal_settings([1, 2, 3])
                    mock_set.assert_not_called()


class TestSetRawMode:
    """Tests for set_raw_mode function."""

    def test_returns_false_on_windows(self):
        """Test Windows returns False."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
            result = set_raw_mode()
            assert result is False

    def test_returns_false_when_no_fileno(self):
        """Test returns False when stdin has no fileno."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            del mock_stdin.fileno
            with patch.object(sys, 'stdin', mock_stdin):
                result = set_raw_mode()
                assert result is False

    def test_returns_false_when_not_tty(self):
        """Test returns False when not TTY."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = False
            with patch.object(sys, 'stdin', mock_stdin):
                result = set_raw_mode()
                assert result is False

    def test_returns_true_on_success(self):
        """Test returns True on successful raw mode set."""
        if platform.system() == 'Windows':
            pytest.skip("Unix-specific test")

        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.return_value = 0
            with patch.object(sys, 'stdin', mock_stdin):
                with patch('folder_extractor.utils.terminal.tty.setraw'):
                    result = set_raw_mode()
                    assert result is True

    def test_handles_exception(self):
        """Test handles exceptions gracefully."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = True
            mock_stdin.fileno.side_effect = Exception("Test error")
            with patch.object(sys, 'stdin', mock_stdin):
                result = set_raw_mode()
                assert result is False


class TestClearLine:
    """Tests for clear_line function."""

    def test_clears_line(self, capsys):
        """Test clear_line prints escape sequence."""
        clear_line()
        captured = capsys.readouterr()
        assert '\r\033[K' in captured.out


class TestMoveCursor:
    """Tests for move_cursor_up and move_cursor_down functions."""

    def test_move_cursor_up(self, capsys):
        """Test move_cursor_up prints escape sequence."""
        move_cursor_up(3)
        captured = capsys.readouterr()
        assert '\033[3A' in captured.out

    def test_move_cursor_up_zero(self, capsys):
        """Test move_cursor_up with zero does nothing."""
        move_cursor_up(0)
        captured = capsys.readouterr()
        assert captured.out == ''

    def test_move_cursor_up_negative(self, capsys):
        """Test move_cursor_up with negative does nothing."""
        move_cursor_up(-1)
        captured = capsys.readouterr()
        assert captured.out == ''

    def test_move_cursor_down(self, capsys):
        """Test move_cursor_down prints escape sequence."""
        move_cursor_down(2)
        captured = capsys.readouterr()
        assert '\033[2B' in captured.out

    def test_move_cursor_down_zero(self, capsys):
        """Test move_cursor_down with zero does nothing."""
        move_cursor_down(0)
        captured = capsys.readouterr()
        assert captured.out == ''

    def test_move_cursor_down_negative(self, capsys):
        """Test move_cursor_down with negative does nothing."""
        move_cursor_down(-1)
        captured = capsys.readouterr()
        assert captured.out == ''


class TestGetTerminalWidth:
    """Tests for get_terminal_width function."""

    def test_windows_uses_shutil(self):
        """Test Windows uses shutil.get_terminal_size."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
            with patch('shutil.get_terminal_size') as mock_size:
                mock_size.return_value = MagicMock(columns=120)
                result = get_terminal_width()
                assert result == 120

    def test_unix_uses_ioctl(self):
        """Test Unix uses ioctl."""
        if platform.system() == 'Windows':
            pytest.skip("Unix-specific test")

        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            with patch('fcntl.ioctl') as mock_ioctl:
                import struct
                mock_ioctl.return_value = struct.pack('HHHH', 24, 100, 0, 0)
                result = get_terminal_width()
                assert result == 100

    def test_returns_default_on_exception(self):
        """Test returns 80 on exception."""
        with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
            with patch('fcntl.ioctl', side_effect=Exception("Test")):
                result = get_terminal_width()
                assert result == 80


class TestFormatProgressBar:
    """Tests for format_progress_bar function."""

    def test_basic_progress(self):
        """Test basic progress bar formatting."""
        result = format_progress_bar(50, 100)
        assert '50%' in result
        assert '50/100' in result

    def test_zero_total(self):
        """Test progress bar with zero total."""
        result = format_progress_bar(0, 0)
        assert '100%' in result

    def test_complete_progress(self):
        """Test 100% progress."""
        result = format_progress_bar(100, 100)
        assert '100%' in result
        assert '█' * 50 in result  # Default width

    def test_custom_width(self):
        """Test custom width."""
        result = format_progress_bar(50, 100, width=20)
        assert '50%' in result

    def test_partial_progress(self):
        """Test partial progress."""
        result = format_progress_bar(25, 100, width=20)
        assert '25%' in result
        assert '25/100' in result


class TestSupportsColor:
    """Tests for supports_color function."""

    def test_returns_false_when_no_isatty(self):
        """Test returns False when stdout has no isatty."""
        mock_stdout = MagicMock(spec=[])  # No isatty
        with patch.object(sys, 'stdout', mock_stdout):
            result = supports_color()
            assert result is False

    def test_returns_false_when_not_tty(self):
        """Test returns False when not TTY."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        with patch.object(sys, 'stdout', mock_stdout):
            result = supports_color()
            assert result is False

    def test_windows_enables_ansi(self):
        """Test Windows enables ANSI colors."""
        if platform.system() != 'Windows':
            pytest.skip("Windows-specific test")

        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        with patch.object(sys, 'stdout', mock_stdout):
            with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
                # On actual Windows, this would test the real ctypes.windll
                result = supports_color()
                # Result depends on actual Windows console capabilities
                assert isinstance(result, bool)

    def test_windows_handles_exception(self):
        """Test Windows handles exceptions when ctypes fails."""
        if platform.system() != 'Windows':
            pytest.skip("Windows-specific test")

        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        with patch.object(sys, 'stdout', mock_stdout):
            with patch('folder_extractor.utils.terminal.platform.system', return_value='Windows'):
                # Simulate ctypes import failure
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == 'ctypes':
                        raise ImportError("No ctypes")
                    return original_import(name, *args, **kwargs)

                with patch.object(builtins, '__import__', mock_import):
                    result = supports_color()
                    assert result is False

    def test_unix_checks_term_env(self):
        """Test Unix checks TERM environment variable."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        with patch.object(sys, 'stdout', mock_stdout):
            with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
                with patch.dict('os.environ', {'TERM': 'xterm-256color'}):
                    result = supports_color()
                    assert result is True

    def test_unix_dumb_terminal(self):
        """Test Unix returns False for dumb terminal."""
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        with patch.object(sys, 'stdout', mock_stdout):
            with patch('folder_extractor.utils.terminal.platform.system', return_value='Linux'):
                with patch.dict('os.environ', {'TERM': 'dumb'}):
                    result = supports_color()
                    assert result is False


class TestColor:
    """Tests for Color class."""

    def test_color_constants(self):
        """Test color constants are defined."""
        assert Color.RESET == '\033[0m'
        assert Color.RED == '\033[31m'
        assert Color.GREEN == '\033[32m'
        assert Color.YELLOW == '\033[33m'
        assert Color.BLUE == '\033[34m'
        assert Color.CYAN == '\033[36m'
        assert Color.BOLD == '\033[1m'

    def test_colorize_with_color_support(self):
        """Test colorize adds color codes."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            result = Color.colorize("test", Color.RED)
            assert result == f"{Color.RED}test{Color.RESET}"

    def test_colorize_without_color_support(self):
        """Test colorize returns plain text without color support."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=False):
            result = Color.colorize("test", Color.RED)
            assert result == "test"

    def test_success_method(self):
        """Test success method."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            result = Color.success("OK")
            assert Color.GREEN in result

    def test_error_method(self):
        """Test error method."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            result = Color.error("FAIL")
            assert Color.RED in result

    def test_warning_method(self):
        """Test warning method."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            result = Color.warning("WARN")
            assert Color.YELLOW in result

    def test_info_method(self):
        """Test info method."""
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            result = Color.info("INFO")
            assert Color.CYAN in result
