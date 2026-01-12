"""
child_windows.py

This module creates functions that create popup windows. So far this includes

- Menubar -> Help -> About GRoller

Author: Wei-Hsu Lin
"""

import tkinter as tk
from tkinter import ttk

def create_help_about(app):
    
    # Create popup window with 1/3 the width and 1/2 the height of root
    popup = tk.Toplevel(app.root)
    popup.wm_title(f"About GRoller {app.groller_ver}")
    win_width = app.settings["ui"]["window_width"]
    win_height = app.settings["ui"]["window_height"]
    popup.geometry(f"{win_width/3:.0f}x{win_height/2:.0f}")
    popup.resizable(False, False)

    paragraph1 = tk.Label(
        popup,
        text= (
            "GRoller is a G-code to G-code transpiler"
        ),
        bg="red")
    paragraph1.pack(side=tk.TOP, fill=tk.X)