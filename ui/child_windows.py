"""
child_windows.py

This module creates functions that create popup windows. So far this includes

- Menubar -> Help -> About GRoller

Author: Wei-Hsu Lin
"""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, font

def create_help_about(app):
    
    # Create popup window with 1/2 the width and 2/3 the height of root
    popup = tk.Toplevel(app.root)
    popup.wm_title(f"About GRoller {app.groller_ver}")
    win_width = app.settings["ui"]["window_width"]
    win_height = app.settings["ui"]["window_height"]
    popup.geometry(f"{win_width/2:.0f}x{2*win_height/3:.0f}")
    popup.resizable(False, False)

    paragraph1 = tk.Label(
        popup,
        text= (
            "GRoller is a G-code to G-code transpiler"
        ),
        bg="red", font=app._label_font)
    paragraph1.pack(side=tk.TOP, fill=tk.X)

def create_help_license(app):

    file_path = "./LICENSE"
    
    # Create popup window with 1/2 the width and 1/2 the height of root
    popup = tk.Toplevel(app.root)
    popup.wm_title(f"GRoller License (GNU GPL v3)")
    win_width = app.settings["ui"]["window_width"]
    win_height = app.settings["ui"]["window_height"]
    popup.geometry(f"{win_width/2:.0f}x{win_height/2:.0f}")
    popup.resizable(False, False)

    # Read the contents of ./LICENSE
    try:
        with open(file_path, 'r') as file:
            license_content = file.read()
    except Exception as e:
        license_content = (
            "Unable to read local license file. Groller is licensed under "
            "GNU General Public License (GPL) v3.0\n"
            "https://www.gnu.org/licenses/gpl-3.0.en.html"
        )

    # Display license content to window
    license_textarea = ScrolledText(
        popup, wrap=tk.WORD, font=app._paragraph_font
    )
    license_textarea.insert(tk.INSERT, license_content)
    license_textarea.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    license_textarea.config(state=tk.DISABLED)