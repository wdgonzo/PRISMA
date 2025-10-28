#!/usr/bin/env python3
"""
PRISMA Data Analyzer Launcher
==============================
Launch the Data Analyzer GUI for visualizing and analyzing XRD datasets.

Usage:
    python run_data_analyzer.py

Author(s): William Gonzalez, Luke Davenport
Date: October 2025
Version: Beta 0.1
"""

import sys
from PyQt5.QtWidgets import QApplication
from XRD.gui.data_analyzer import DataAnalyzer


def main():
    """Launch the Data Analyzer GUI."""
    app = QApplication(sys.argv)
    window = DataAnalyzer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
