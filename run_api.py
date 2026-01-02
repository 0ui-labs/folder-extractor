#!/usr/bin/env python3
"""
API Server Entry Point for Folder Extractor.

This module provides a user-friendly entry point for starting the FastAPI server
with Uvicorn. It supports configuration via CLI arguments and environment variables,
with CLI arguments taking precedence.

Usage:
    python run_api.py                          # Default: localhost:23456
    python run_api.py --port 8000              # Custom port
    python run_api.py --reload                 # Development mode with auto-reload
    python run_api.py --host 0.0.0.0 --port 8080 --log-level debug

Environment Variables:
    API_HOST      - Server host (default: 127.0.0.1)
    API_PORT      - Server port (default: 23456)
    API_LOG_LEVEL - Logging level (default: info)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for CLI configuration.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Start the Folder Extractor API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_api.py                              Start with defaults (localhost:23456)
  python run_api.py --port 8000                  Use custom port
  python run_api.py --reload                     Enable hot-reload for development
  python run_api.py --host 0.0.0.0 --workers 4   Production setup with multiple workers

Environment Variables:
  API_HOST, API_PORT, API_LOG_LEVEL can be set in .env file.
  CLI arguments override environment variables.
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Server host address (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=23456,
        help="Server port (default: 23456)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development (default: False)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="Logging level (default: info)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1, ignored with --reload)",
    )

    return parser


def get_config(args_list: list[str] | None = None) -> dict[str, Any]:
    """
    Get server configuration from CLI arguments and environment variables.

    CLI arguments take precedence over environment variables.
    Environment variables take precedence over built-in defaults.

    Args:
        args_list: Optional list of CLI arguments (for testing).
                   If None, uses sys.argv.

    Returns:
        Configuration dictionary with keys: host, port, reload, log_level, workers.
    """
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed, continue without it

    parser = create_parser()

    # Parse CLI arguments: use sys.argv when None, otherwise use provided list
    if args_list is None:
        args = parser.parse_args()  # Uses sys.argv[1:]
        cli_source = sys.argv
    else:
        args = parser.parse_args(args_list)  # Uses provided list (for testing)
        cli_source = args_list

    # Get environment variable defaults
    env_host = os.getenv("API_HOST", "127.0.0.1")
    env_port = int(os.getenv("API_PORT", "23456"))
    env_log_level = os.getenv("API_LOG_LEVEL", "info")

    # Determine final values: CLI overrides ENV overrides defaults
    # Check if CLI arg was explicitly provided by checking cli_source
    final_host = args.host if "--host" in cli_source else env_host
    final_port = args.port if "--port" in cli_source else env_port
    final_log_level = args.log_level if "--log-level" in cli_source else env_log_level

    return {
        "host": final_host,
        "port": final_port,
        "reload": args.reload,
        "log_level": final_log_level,
        "workers": args.workers,
    }


def get_uvicorn_config(
    host: str,
    port: int,
    reload: bool,
    log_level: str,
    workers: int,
) -> dict[str, Any]:
    """
    Generate Uvicorn configuration dictionary.

    Args:
        host: Server host address.
        port: Server port.
        reload: Enable hot-reload mode.
        log_level: Logging level.
        workers: Number of worker processes.

    Returns:
        Configuration dictionary for uvicorn.run().
    """
    config: dict[str, Any] = {
        "app": "folder_extractor.api.server:app",
        "host": host,
        "port": port,
        "reload": reload,
        "log_level": log_level,
        "access_log": True,
    }

    # Workers only applicable when not in reload mode
    if not reload and workers > 1:
        config["workers"] = workers

    return config


def print_startup_message(host: str, port: int) -> None:
    """
    Print informative startup message.

    Args:
        host: Server host address.
        port: Server port.
    """
    print(f"\n{'=' * 60}")
    print("  Folder Extractor API Server")
    print(f"{'=' * 60}")
    print(f"  Server:  http://{host}:{port}")
    print(f"  Docs:    http://{host}:{port}/docs")
    print(f"  ReDoc:   http://{host}:{port}/redoc")
    print(f"{'=' * 60}\n")


def format_import_error_message(module_name: str) -> str:
    """
    Format a helpful error message for import failures.

    Args:
        module_name: Name of the module that failed to import.

    Returns:
        User-friendly error message with installation hints.
    """
    return (
        f"Error: Could not import API module '{module_name}'.\n"
        f"\n"
        f"Please ensure all dependencies are installed:\n"
        f"  pip install fastapi uvicorn[standard] python-dotenv\n"
        f"\n"
        f"If using development mode:\n"
        f"  pip install -e .\n"
    )


def main(args_list: list[str] | None = None) -> int:
    """
    Main entry point for the API server.

    Args:
        args_list: Optional list of CLI arguments (for testing).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    try:
        import uvicorn
    except ImportError:
        print(
            "Error: uvicorn not installed.\n"
            "Please install: pip install uvicorn[standard]"
        )
        return 1

    try:
        # Validate that the API module can be imported
        from folder_extractor.api import server as _  # noqa: F401
    except ImportError as e:
        print(format_import_error_message("folder_extractor.api.server"))
        print(f"Original error: {e}")
        return 1

    config = get_config(args_list)

    print_startup_message(config["host"], config["port"])

    uvicorn_config = get_uvicorn_config(
        host=config["host"],
        port=config["port"],
        reload=config["reload"],
        log_level=config["log_level"],
        workers=config["workers"],
    )

    try:
        uvicorn.run(**uvicorn_config)
        return 0
    except KeyboardInterrupt:
        print("\n  Server stopped by user (Ctrl+C)")
        return 0
    except Exception as e:
        print(f"\n  Error starting server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
