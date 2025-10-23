"""
PRISMA Initialization Script
============================
Setup and initialization for GSAS-II scripting environment.

Author(s): William Gonzalez
Date: October 2025
Version: Beta 0.1
"""

import subprocess
import sys
import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as messagebox

def initialize_gsas():
    def select_folder():
        global folder_path
        folder_path = filedialog.askdirectory(title="Select a Folder")
        if folder_path:
            label.config(text=f"Selected Folder: {folder_path}")

    def run_secondary_script():
        global folder_path
        if folder_path:
            # Example: Run a secondary script or function
            # For demonstration, let's just print the folder path
            print(f"Running script with folder: {folder_path}")
            sys.path.insert(0, folder_path)  # needed to find GSASII package
            try:
                from GSASII import GSASIIscriptable as G2sc  # type: ignore
                G2sc.installScriptingShortcut()
                print("Sucessfully initialized GSAS Scripting!")
                messagebox.showinfo("Success", "GSAS Scripting successfully initialized!")
            except ImportError as e:
                print(f"Failed to import GSASII. Error: {e}")
                messagebox.showerror("Error", f"Failed to import GSASII. Error: {e}")
            root.destroy()
        else:
            print("No folder selected. Please select a folder first.")
            messagebox.showwarning("No Folder", "No folder selected. Please select a folder first.")

    # Create the main window
    root = tk.Tk()
    root.title("Folder Selector")

    label = tk.Label(root, text="Please open GSAS-II and install the GSASscriptable shortcut before running!")
    label.pack(pady=20)

    # Create a button to open the folder dialog
    button_select = tk.Button(root, text="Select Folder", command=select_folder)
    button_select.pack(pady=20)

    # Create a label to display the selected folder path
    label = tk.Label(root, text="No folder selected")
    label.pack(pady=20)

    # Create a button to run the secondary script
    button_run = tk.Button(root, text="Run initialization", command=run_secondary_script)
    button_run.pack(pady=20)

    # Initialize folder_path variable
    folder_path = None

    # Run the application
    root.mainloop()

def initialize_python(packages):
    """Install a list of packages using pip."""
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}. Error: {e}")

if __name__ == "__main__":
    packages_to_install = [
        "numpy>=2.0,<3.0",  # NumPy 2.x (compatible with Python 3.10+)
        "pandas",
        "dask[distributed]",
        "dask",
        "dask-mpi",  # For HPC multi-node scaling
        "mpi4py",    # MPI support for distributed computing
        "matplotlib",
        "seaborn",
        "imageio",
        "tqdm",
        "scipy",
        "pyqt5",
        "openpyxl",
        "pybaselines",
        "bokeh",
        "zarr[v3]",
        "numcodecs>=0.12.0",
        "threadpoolctl",
        "psutil",
        "fabio"  # For multi-frame EDF/GE5 image support
        #"tkinter"
    ]
    initialize_python(packages_to_install)
    initialize_gsas()
    # Show a message box at the end to confirm completion
    tk.Tk().withdraw()
    messagebox.showinfo("Initialization Complete", "All packages installed and GSAS initialized.")