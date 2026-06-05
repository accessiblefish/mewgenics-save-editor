#!/usr/bin/env python3
"""
Setup script for Mewgenics Save Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
with open(readme_path, encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mewgenics-save-tool",
    version="1.0.0",
    description="A Python CLI tool for editing Mewgenics save files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="accessiblefish",
    url="https://github.com/accessiblefish/mewgenics-save-tool",
    py_modules=["mewgenics_save_tool"],
    install_requires=[
        "lz4>=4.0.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "mewgenics-save-tool=mewgenics_save_tool:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment",
        "Topic :: Utilities",
    ],
    keywords="mewgenics save editor game tool",
)
