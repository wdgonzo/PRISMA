"""
PRISMA Setup Script
===================
Installation configuration for PRISMA - Parallel Refinement and Integration
System for Multi-Azimuthal Analysis.

Install with: pip install -e .
Or: python setup.py install
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version from XRD/__init__.py
version_file = Path(__file__).parent / "XRD" / "__init__.py"
version = "0.3.0-beta"  # Default
if version_file.exists():
    for line in version_file.read_text(encoding="utf-8").split("\n"):
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    for line in requirements_file.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

setup(
    name="PRISMA",
    version=version,
    author="William Gonzalez, Adrian Guzman, Luke Davenport",
    author_email="wgonzalez@example.com",  # TODO: Update with actual email
    description="Parallel Refinement and Integration System for Multi-Azimuthal XRD Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wdgonzo/PRISMA",
    project_urls={
        "Bug Tracker": "https://github.com/wdgonzo/PRISMA/issues",
        "Documentation": "https://github.com/wdgonzo/PRISMA/blob/main/README.md",
        "Source Code": "https://github.com/wdgonzo/PRISMA",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Chemistry",
        "License :: OSI Approved",  # TODO: Update when license chosen
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=3.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
    },
    entry_points={
        "console_scripts": [
            "prisma=run_prisma:main",
            "prisma-recipe-builder=run_recipe_builder:main",
            "prisma-batch=run_batch_processor:main",
            "prisma-analyzer=run_data_analyzer:main",
            "prisma-verify=XRD.tools.verify_installation:main",
        ],
    },
    include_package_data=True,
    package_data={
        "XRD": [
            "gui/*.py",
            "core/*.py",
            "processing/*.py",
            "visualization/*.py",
            "hpc/*.py",
            "utils/*.py",
            "tools/*.py",
        ],
    },
    zip_safe=False,
    keywords="xrd x-ray diffraction materials science gsas synchrotron strain analysis",
)
