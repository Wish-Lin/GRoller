"""
menubar.py

This module creates the menubar of the app. Only one public function is
located here: create_menubar()

Author: Wei-Hsu Lin
"""

import platform
import tkinter as tk
from tkinter import ttk
from .child_windows import *

def create_menubar(app: MainApp):
    """
    Creates the entire menubar of the GUI

    The current (v0.1.0) menubar is
        File|Edit|Help

    Args:
        app (MainApp): The app instance

    Returns:
        None
    """
    # Set correct modifier depending on OS. macOS uses ⌘ and everyone else
    # (i.e, Windows and Linux) uses Ctrl
    modifier = "⌘" if platform.system() == "Darwin" else "Ctrl"

    menubar = tk.Menu(app.root)
    # 1 -- File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(
        label="New File",
        accelerator=f"{modifier}+N",
        #command=app.newfile
    )
    file_menu.add_command(
        label="Open...",
        accelerator=f"{modifier}+O",
        command=app._open_file
    )
    file_menu.add_command(
        label="Open Recent...",
        #command=app._open_file
    )
    file_menu.add_separator()
    file_menu.add_command(
        label="Save...",
        accelerator=f"{modifier}+S",
        #command=app._open_file
    )
    file_menu.add_command(
        label="Save As...",
        accelerator=f"{modifier}+Shift+S",
        #command=app._open_file
    )
    file_menu.add_separator()
    file_menu.add_command(
        label="Exit",
        accelerator=f"{modifier}+Q",
        command=app.root.destroy
    )
    # 2 -- Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    # 3 -- Help Menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(
        label="About GRoller",
        command=lambda: create_help_about(app)
    )
    help_menu.add_command(
        label="License",
        command=lambda: create_help_license(app)
    )
    
    # Generate menubar then set it as app.root's menubar
    menubar.add_cascade(label="File", menu=file_menu)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    menubar.add_cascade(label="Help", menu=help_menu)
    app.root.config(menu=menubar)

    # Attach menubar to app for later access
    app.menubar = menubar


