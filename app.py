"""
app.py

This module defines the MainApp class, the GUI of GRoller. Note that
most of the actual GUI code are located in the modules

Author: Wei-Hsu Lin
"""


import tkinter as tk
from tkinter import filedialog, messagebox
import sys, json, re, traceback
from pathlib import Path

from ui.menubar import create_menubar
from ui.layout import create_layout
from transpiler import xgc_to_gcode, grant_gui_access


class MainApp(tk.Tk):
    # Some internal variables
    groller_ver = "0.1.0"
    program_title = f"GRoller {groller_ver}"

    def __init__(self):
        super().__init__()

        # Create a blank window
        self.title(self.program_title)
        self.geometry("1600x900") # Fits most screens now in 2025
        self.resizable(False, False)
        self._set_icon()

        self._load_settings()
        self._set_hotkey_bindings()

        create_menubar(self)
        create_layout(self)

        # Injects self into the global of py_execute.py. End goal is to allow
        # user XGC script to interact with the app (e.g, console_print)
        grant_gui_access(self)

    def _set_icon(self) -> None:
        """
        Set the window icon for the application.

        The icon file is ./assets/icon.png. If the icon file
        does not exist, no icon is set.

        Returns:
            None
        """
        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            icon_image = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, icon_image)

    def _set_hotkey_bindings(self) -> None:
        """
        Set the window icon for the application.

        The icon file is ./assets/icon.png. If the icon file
        does not exist, no icon is set.

        Returns:
            None
        """
        event_key_bindings = {
            self._select_all: [
                "<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"
            ],
        }
        eventless_key_bindings = {
            self.destroy: [
                "<Control-q>", "<Control-Q>", "<Command-q>", "<Command-Q>"
            ],
            self._open_file: [
                "<Control-o>", "<Control-O>", "<Command-o>", "<Command-O>"
            ],
        }
        for func, hotkeys in event_key_bindings.items():
            for hotkey in hotkeys:
                self.bind_all(hotkey, lambda event, f=func: f(event))
        for func, hotkeys in eventless_key_bindings.items():
            for hotkey in hotkeys:
                self.bind_all(hotkey, lambda event, f=func: f())
    
    def _open_file(self) -> None:
        """
        Open an extended G-code file (.xgc) and load to editor

        This function can be called from the file menu, by Ctrl+O in 
        Windows/Linux, or by Command+O in macOS. 

        Returns:
            None
        """
        file_path = tk.filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("GRoller Extended G-code Files", "*.xgc"),
                ("All Files", "*.*")
            ]
        )
        if not file_path:
            return  # Action cancelled by user
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Clear the entire xgc editor then insert the file content
        self.xgc_editor.delete("1.0", tk.END)
        self.xgc_editor.insert(tk.END, content)
        self.xgc_editor_linenums.redraw() # Update linenum display
    
    def _select_all(self, event: tk.Event):
        """
        Select all text in the widget (tk.Entry and tk.Text only)

        Args:
            event (tk.Event): 
                event.widget is the widget to perform this operation.

        Returns:
            str: Returns "break" to prevent the default behavior.
        """
        widget = event.widget
        if isinstance(widget, tk.Entry): # tk.Entry = single line text box
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        elif isinstance(widget, tk.Text):  # tk.Text = textarea
            widget.tag_add("sel", "1.0", "end-1c")
        return "break"  # prevent default behavior
    
    def _reset_console(self):
        self.console.config(state=tk.NORMAL)
        self.console.delete("1.0", tk.END)
        self.console.insert(tk.END, self.console_header)
        self.console.config(state=tk.DISABLED)

    def _console_printline(self, text: str, type: str, addline: bool) -> None:
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, f"{text}")

        # Add highlighting to line, from line_num.0 to line_num.end
        line_num = self.console.index("end-1c").split(".")[0]
        self.console.tag_add(type, f"{line_num}.0", f"{line_num}.end")

        # Add the unhighlighted dashed line if needed
        if addline:
            self.console.insert(tk.END, f"\n{self.console_hline}")
        
        # Add newline, scroll to newest line and disable editing again
        self.console.insert(tk.END, "\n")
        self.console.see(tk.END) 
        self.console.config(state=tk.DISABLED)

    def _compile(self):
        self.result_output.config(state=tk.NORMAL)
        self.result_output.delete("1.0", tk.END)
        xgc_script = self.xgc_editor.get("1.0", "end-1c")

        # Read max_dec_prec from settings dict, might still fail if user messed
        # settings.json in a legal way. In that case fall back to default 3
        try:
            max_dec_prec = self.settings["comp_param"]["max_dec_prec"]
            if not isinstance(max_dec_prec, int):
                max_dec_prec = 3
                self._console_printline(
                    (
                        "Warning: Max decimal precision is not an integer. "
                        "Default value of 3 is used. [settings.json]"
                    ),
                    "warning", True)
        except KeyError:
            max_dec_prec = 3
            self._console_printline(
                (
                    "Warning: Max decimal precision not found. Default value "
                    "of 3 is used. [settings.json]"
                ),
                "warning", True)
        try:
            gcode_script = xgc_to_gcode(xgc_script, (max_dec_prec,2))
        except Exception as e: # Compilation failed
            # Get the traceback object and check if the exception occured
            # before or after the exec() stage.abs
            traceback_str = traceback.format_exc()
            match = re.search( # This line only shows up in exec() layer
                r"File \"<string>\", line (\d+), in <module>",
                traceback_str
            )
            if match: # Error occured in exec()
                line_number = int(match.group(1))
                self._console_printline(
                    f"Python exec() Error: Line {line_number}:", 
                    "error", False)
                self._console_printline(f"{e}", "error", True)
            else: # Error occured in preprocessing to Python
                self._console_printline(
                    f"Preprocessor Error:", "error", False)
                print(e)
                self._console_printline(e, "error", True)
            self.result_output.insert(tk.END, "Compilation Failed")
        else:
            # Compilation Successful
            self._console_printline("Compilation Success!", "success", True)
            self.result_output.insert(tk.END, gcode_script)
        finally:
            # Disable result_output again and trigger linenumber redraw
            self.result_output.config(state=tk.DISABLED)
            self.result_output_linenums.redraw()
        return "break"

    def _load_settings(self):
        # Load settings from settings.json in the same directory
        # Show messagebox then abort if settings fail to load
        try:
            settings_file = Path(__file__).with_name("settings.json")
            with settings_file.open("r", encoding="utf-8") as f:
                self.settings = json.load(f)
                # print(self.settings)
        except Exception as e:
            self.lift() 
            # Reliably ensures the messagebox is on top of the main window 
            tk.messagebox.showerror(
                "Error loading settings.json",
                f"{e.__class__.__name__}: {e}",
                parent=self
            )
            self.destroy()
            sys.exit(0)