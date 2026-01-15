"""
Subtitle Generator Package Setup.

This package provides a modular subtitle generation system using Whisper.cpp.
"""

from setuptools import setup, find_packages
import os

# Read version from package
version = "2.0.0"

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
with open(readme_path, "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
requirements = []
if os.path.exists(requirements_path):
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and options
            if line and not line.startswith("#") and not line.startswith("-"):
                requirements.append(line)

setup(
    name="subtitle-generator",
    version=version,
    author="Ved Gupta",
    description="Generate subtitles for videos using Whisper.cpp",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/innovatorved/subtitle",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Multimedia :: Video",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "subtitle=src.cli.commands:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml"],
    },
)
