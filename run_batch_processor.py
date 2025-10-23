#!/usr/bin/env python3
"""
PRISMA Batch Processor Launcher
================================
Launch the batch processor for processing multiple recipes sequentially.

Usage:
    python run_batch_processor.py                  # Process all recipes in recipes/
    python run_batch_processor.py recipe.json      # Process single recipe
    python run_batch_processor.py --help           # Show help information

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import sys
from XRD.processing.batch_processor import main as batch_main


if __name__ == "__main__":
    batch_main()
