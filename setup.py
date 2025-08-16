"""Setup script for MetaCLI."""

from pathlib import Path
from setuptools import setup, find_packages

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8') if (this_directory / "README.md").exists() else ""

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                requirements.append(line)

setup(
    name="metacli",
    version="1.0.0",
    author="MetaCLI Development Team",
    author_email="dev@metacli.com",
    description="A powerful command-line interface for extracting, processing, and managing file metadata",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/metacli/metacli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
        "Topic :: Multimedia",
        "Topic :: Text Processing",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "full": [
            "pyyaml>=6.0",
            "tabulate>=0.9.0",
            "openpyxl>=3.0.0",
            "chardet>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "metacli=metacli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "metacli": ["py.typed"],
    },
    keywords=[
        "metadata",
        "cli",
        "file-processing",
        "exif",
        "audio-metadata",
        "video-metadata",
        "document-metadata",
        "file-management",
    ],
    project_urls={
        "Bug Reports": "https://github.com/metacli/metacli/issues",
        "Source": "https://github.com/metacli/metacli",
        "Documentation": "https://metacli.readthedocs.io/",
    },
)