#!/usr/bin/env python3
"""
Test runner for Folder Extractor.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py unit         # Run only unit tests
    python run_tests.py integration  # Run only integration tests
    python run_tests.py performance  # Run performance benchmarks
    python run_tests.py coverage     # Run with coverage report
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    """Main test runner."""
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Determine what to run
    test_type = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    # Install test dependencies
    # Always run pip install to ensure all test dependencies are available
    # pip is smart enough to skip already-installed packages
    print("Installing test dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[test]"],
        capture_output=True,  # Suppress verbose pip output
    )

    exit_code = 0

    if test_type == "unit":
        exit_code = run_command("pytest tests/unit -v", "Running Unit Tests")

    elif test_type == "integration":
        exit_code = run_command(
            "pytest tests/integration -v", "Running Integration Tests"
        )

    elif test_type == "performance":
        exit_code = run_command(
            "pytest tests/performance -v -m benchmark", "Running Performance Benchmarks"
        )

    elif test_type == "coverage":
        exit_code = run_command(
            "pytest --cov=folder_extractor --cov-report=html --cov-report=term",
            "Running Tests with Coverage",
        )
        print("\nCoverage report generated in htmlcov/index.html")

    elif test_type == "all":
        # Run all test types
        test_types = [
            ("pytest tests/unit -v", "Running Unit Tests"),
            ("pytest tests/integration -v", "Running Integration Tests"),
            (
                "pytest tests/performance -v -m benchmark -k 'not test_'",
                "Running Quick Benchmarks",
            ),
        ]

        for cmd, desc in test_types:
            code = run_command(cmd, desc)
            if code != 0:
                exit_code = code

    else:
        print(f"Unknown test type: {test_type}")
        print(__doc__)
        exit_code = 1

    # Print summary
    print(f"\n{'=' * 60}")
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print(f"{'=' * 60}\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
