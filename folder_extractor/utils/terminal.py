"""
Terminal handling utilities.

Provides functions for terminal settings management
and output formatting.
"""
import os
import sys
import platform
from typing import Optional, List

# Only import termios on Unix-like systems
if platform.system() != 'Windows':  # pragma: no cover (Unix/macOS only)
    import termios
    import tty


def save_terminal_settings() -> Optional[List]:
    """
    Save current terminal settings.
    
    Returns:
        Terminal settings list or None on Windows/error
    """
    if platform.system() == 'Windows':
        return None
    
    try:
        if hasattr(sys.stdin, 'fileno') and sys.stdin.isatty():
            return termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass
    
    return None


def restore_terminal_settings(settings: Optional[List]) -> None:
    """
    Restore terminal settings.
    
    Args:
        settings: Previously saved terminal settings
    """
    if platform.system() == 'Windows' or settings is None:
        return
    
    try:
        # Note: Branch coverage with mocked stdin doesn't track correctly
        # in pytest-cov, but the path is tested in test_restores_on_unix_tty
        if hasattr(sys.stdin, 'fileno') and sys.stdin.isatty():  # pragma: no branch
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, settings)
    except Exception:
        pass


def set_raw_mode() -> bool:
    """
    Set terminal to raw mode for key detection.
    
    Returns:
        True if successful, False otherwise
    """
    if platform.system() == 'Windows':
        return False
    
    try:
        if hasattr(sys.stdin, 'fileno') and sys.stdin.isatty():
            tty.setraw(sys.stdin.fileno())
            return True
    except Exception:
        pass
    
    return False


def clear_line() -> None:
    """
    Clear the current terminal line.
    """
    print('\r\033[K', end='', flush=True)


def move_cursor_up(lines: int = 1) -> None:
    """
    Move cursor up by specified number of lines.
    
    Args:
        lines: Number of lines to move up
    """
    if lines > 0:
        print(f'\033[{lines}A', end='', flush=True)


def move_cursor_down(lines: int = 1) -> None:
    """
    Move cursor down by specified number of lines.
    
    Args:
        lines: Number of lines to move down
    """
    if lines > 0:
        print(f'\033[{lines}B', end='', flush=True)


def get_terminal_width() -> int:
    """
    Get terminal width in characters.
    
    Returns:
        Terminal width or 80 as default
    """
    try:
        if platform.system() == 'Windows':
            # Windows-specific method
            import shutil
            return shutil.get_terminal_size().columns
        else:
            # Unix-like systems
            import fcntl
            import struct
            h, w, hp, wp = struct.unpack('HHHH',
                fcntl.ioctl(0, termios.TIOCGWINSZ,
                struct.pack('HHHH', 0, 0, 0, 0)))
            return w
    except Exception:
        return 80  # Default width


def format_progress_bar(current: int, total: int, width: int = 50) -> str:
    """
    Format a progress bar string.
    
    Args:
        current: Current progress value
        total: Total value
        width: Width of the progress bar
    
    Returns:
        Formatted progress bar string
    """
    if total == 0:
        percentage = 100
    else:
        percentage = int((current / total) * 100)
    
    filled = int((current / total) * width) if total > 0 else width
    bar = '█' * filled + '░' * (width - filled)
    
    return f"[{bar}] {percentage}% ({current}/{total})"


def supports_color() -> bool:
    """
    Check if terminal supports color output.
    
    Returns:
        True if color is supported
    """
    # Check if output is to a terminal
    if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
        return False
    
    # Check platform
    if platform.system() == 'Windows':  # pragma: no cover
        # Windows 10+ supports ANSI colors
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    
    # Unix-like systems usually support color
    term = os.environ.get('TERM', '')
    return term != 'dumb'


class Color:
    """ANSI color codes for terminal output."""
    
    # Reset
    RESET = '\033[0m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text if supported."""
        if supports_color():
            return f"{color}{text}{cls.RESET}"
        return text
    
    @classmethod
    def success(cls, text: str) -> str:
        """Format success message."""
        return cls.colorize(text, cls.GREEN)
    
    @classmethod
    def error(cls, text: str) -> str:
        """Format error message."""
        return cls.colorize(text, cls.RED)
    
    @classmethod
    def warning(cls, text: str) -> str:
        """Format warning message."""
        return cls.colorize(text, cls.YELLOW)
    
    @classmethod
    def info(cls, text: str) -> str:
        """Format info message."""
        return cls.colorize(text, cls.CYAN)