#!/usr/bin/env python3
"""
PRISMA Recipe Builder Launcher
===============================
Launch the Recipe Builder GUI for creating XRD processing recipes.

Usage:
    python run_recipe_builder.py

Author(s): William Gonzalez, Adrian Guzman
Date: October 2025
Version: Beta 0.1
"""

import sys
from PyQt5.QtWidgets import QApplication
from XRD.gui.recipe_builder import RecipeBuilderWindow


def main():
    """Launch the Recipe Builder GUI."""
    app = QApplication(sys.argv)
    window = RecipeBuilderWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
