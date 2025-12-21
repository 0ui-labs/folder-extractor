#!/usr/bin/env python3
"""
Setup-Skript für Folder Extractor
Ermöglicht die Installation via pip
"""

from pathlib import Path

from setuptools import find_packages, setup

# README einlesen
this_directory = Path(__file__).parent
long_description = (
    (this_directory / "README.md").read_text(encoding="utf-8")
    if (this_directory / "README.md").exists()
    else ""
)

setup(
    name="folder-extractor",
    version="1.3.3",
    author="Philipp Briese",
    author_email="",
    description="Ein sicheres Tool zum Extrahieren von Dateien aus Unterordnern",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/folder-extractor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "folder-extractor=folder_extractor.main:main",
        ],
    },
    # Runtime dependencies for modern CLI experience
    install_requires=[
        "rich>=13.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-benchmark>=4.0",
            "pytest-xdist>=3.0",
            "hypothesis>=6.0",
        ],
    },
    keywords="folder, extractor, organize, files, directory, cleanup",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/folder-extractor/issues",
        "Source": "https://github.com/yourusername/folder-extractor",
    },
)
