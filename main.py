"""
main.py

Entry point of this app

Author: Wei-Hsu Lin
"""

import tkinter as tk
from app import MainApp

# Entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()