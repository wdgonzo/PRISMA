#!/usr/bin/env python3
"""
Launcher for Advanced XRD Visualization Interface
=================================================
Simple launcher that handles Unicode encoding issues on Windows.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import sys
import os

def main():
    """Launch the advanced interface with error handling."""
    print("Launching Advanced XRD Visualization Interface...")

    try:
        # Set environment to handle Unicode
        if sys.platform.startswith('win'):
            os.environ['PYTHONIOENCODING'] = 'utf-8'

        # Import and launch the interface
        from XRD.gui.advanced_visualization_interface import main as interface_main
        interface_main()

    except UnicodeEncodeError as e:
        print("Warning: Unicode display issue detected (Windows console limitation)")
        print("Interface functionality is not affected.")

        # Try launching without emoji output
        try:
            from XRD.gui.advanced_visualization_interface import AdvancedVisualizationWindow
            from PyQt5.QtWidgets import QApplication

            app = QApplication(sys.argv)

            # Simple styling
            app.setStyleSheet("""
                QWidget {
                    background-color: white;
                    color: black;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid gray;
                    margin: 5px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #999;
                    padding: 5px;
                    color: black;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)

            window = AdvancedVisualizationWindow()
            window.show()

            print("Advanced interface launched successfully!")
            print("Note: Some emoji characters may not display in console, but GUI works normally.")

            sys.exit(app.exec_())

        except Exception as e2:
            print(f"Error launching interface: {e2}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nTroubleshooting:")
        print("1. Make sure you're in the correct directory")
        print("2. Check that all required packages are installed")
        print("3. Verify Zarr data exists (use interface.py to generate)")
        input("Press Enter to exit...")
        sys.exit(1)