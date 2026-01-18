"""
app.py

This module defines the MainApp class, the GUI of GRoller. Note that
most of the actual GUI code are located in the modules

Author: Wei-Hsu Lin
"""

import sys, re, traceback, json
import tkinter as tk
from tkinter import filedialog, messagebox, font
from pathlib import Path
from datetime import datetime


from ui.menubar import create_menubar
from ui.layout import create_layout
from transpiler import xgc_to_gcode, grant_gui_access


class MainApp:
    def __init__(self, root: tk.Tk) -> None:
        """
        Class init. Calls a bunch of functions sequentially to set up the app.

        Parameters
        ----------
        root : tk.Tk
            The root window of the app. MainApp exist as a wrapper of root so
            my app's logic doesn't interfere with tkinter.

        Returns
        -------
        None
        """
        # Set internal variables, including the most important one: root
        self.root = root
        self.groller_ver = "0.1.0"
        self.program_title = f"GRoller {self.groller_ver}"
        self.settings_json_path = Path(__file__).with_name("settings.json")

        # Read settings from file
        # Only if the reading is success will the app start
        self._read_settings()
        # Load and validate seetings (misc.)
        self._load_settings()

        # Create a blank window
        self.root.title(self.program_title)
        self.root.geometry("1600x900") # Fits most screens now in 2025
        self.root.resizable(False, False)

        # Set icon and root-level hotkeys
        self._set_icon()
        self._set_root_hotkeys()

        # UI generation, pass the tkinter window in for processing
        create_menubar(self)
        create_layout(self)

        # Injects self into the global of py_execute.py. The goal is to allow
        # XGC script to interact with the GUI (e.g, console_print).
        grant_gui_access(self)

    def _set_icon(self) -> None:
        """
        Set the window icon for the application.

        The icon file is /assets/icon.png. If the icon file does not exist, 
        no icon is set and that's fine.

        Returns
        -------
        None
        """
        icon_path = Path(__file__).parent/"assets"/"brand"/"icon_600x600.png"
        if icon_path.exists():
            icon_image = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, icon_image)

    def _set_root_hotkeys(self) -> None:
        """
        Set root level (global) hotkeys
        
        Both Ctrl and Command(⌘) based combos are set in one go to ensure 
        cross platform compatibility.

        Returns
        -------
        None
        """
        # Operations that require info of the event widget
        event_key_bindings = {
            self._select_all: [
                "<Control-a>", "<Control-A>", "<Command-a>", "<Command-A>"
            ],
        }
        # Operation they don't require info of the event widget
        eventless_key_bindings = {
            self.root.destroy: [
                "<Control-q>", "<Control-Q>", "<Command-q>", "<Command-Q>"
            ],
            self._new_file: [
                "<Control-n>", "<Control-N>", "<Command-n>", "<Command-N>"
            ],
            self._open_file: [
                "<Control-o>", "<Control-O>", "<Command-o>", "<Command-O>"
            ],
            self._save_file: [
                "<Control-s>", "<Control-S>", "<Command-s>", "<Command-S>"
            ],
        }
        # Bind all hotkeys to root. To prevent late binding, lambda is used.
        for func, hotkeys in event_key_bindings.items():
            for hotkey in hotkeys:
                self.root.bind_all(hotkey, lambda event, f=func: f(event))
        for func, hotkeys in eventless_key_bindings.items():
            for hotkey in hotkeys:
                self.root.bind_all(hotkey, lambda event, f=func: f())
    
    def _open_file(self) -> None:
        """
        Open an extended G-code file (.xgc) and load to editor

        This function can be called from the file menu, by Ctrl+O in 
        Windows/Linux, or by Command+O in macOS. 

        Returns
        -------
        None
        """
        file_path = tk.filedialog.askopenfilename(
            title="Open File",
            filetypes=[
                ("GRoller Extended G-code Files", "*.xgc"),
                ("All Files", "*.*")
            ]
        )
        if not file_path: # Action cancelled by user
            return  
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Clear xgc editor and insert file content
        self.xgc_editor.delete("1.0", tk.END)
        self.xgc_editor.insert(tk.END, content)
        self.xgc_editor_linenums.redraw()
        
        # Clear result output
        self.result_output.config(state=tk.NORMAL)
        self.result_output.delete("1.0", tk.END)
        self.result_output_linenums.redraw()
        self.result_output.config(state=tk.DISABLED)

    def _new_file(self) -> None:
        """
        Create a new extended G-code file (.xgc) at the user-specified location

        This function can be called from the file menu, by Ctrl+N in 
        Windows/Linux, or by Command+N in macOS. 

        Returns
        -------
        None
        """
        file_path = tk.filedialog.asksaveasfilename(
            title="New File",
            filetypes=[
                ("GRoller Extended G-code Files", "*.xgc"),
            ]
        )
        if not file_path: # Action cancelled by user
            return  

        # Create empty file and write nothing to it
        with open(file_path, "w", encoding="utf-8") as f:
            pass 

        # Set current_file setting to user input, then clear both editors
        self.settings["file_io"]["current_file"] = file_path
        self._save_settings_to_json()
        self.xgc_editor.delete("1.0", tk.END)
        self.xgc_editor_linenums.redraw()

        self.result_output.config(state=tk.NORMAL)
        self.result_output.delete("1.0", tk.END)
        self.result_output_linenums.redraw()
        self.result_output.config(state=tk.DISABLED)
    
    def _save_file(self) -> None:
        """
        Save the contents of the editor to files

        This function can be called from the file menu, by Ctrl+S in 
        Windows/Linux, or by Command+S in macOS. 

        Returns
        -------
        None
        """
        # G-code file is stored in the same location as the xgc file, and
        # with the same name. Create if nonexistent and overwrite otherwise
        xgc_path = Path(self.settings["file_io"]["current_file"])
        gc_ext = self.settings["file_io"]["gcode_file_extension"]
        gcode_path = xgc_path.with_name(f"{xgc_path.stem}.{gc_ext}")
        
        # Get both scripts from editor
        xgc_script = self.xgc_editor.get("1.0", "end-1c")
        gcode_script = self.result_output.get("1.0", "end-1c")

        # Write both scripts to file
        xgc_path.write_text(xgc_script)
        gcode_path.write_text(gcode_script)

    def _select_all(self, event: tk.Event) -> None:
        """
        Select all text in the widget (tk.Entry and tk.Text only)

        Parameters
        ----------
        event : tk.Event
            Object that contains the event widget, the current widget in focus

        Returns
        -------
        None
        """
        widget = event.widget
        if isinstance(widget, tk.Entry): # tk.Entry = single line text box
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        elif isinstance(widget, tk.Text):  # tk.Text = textarea
            widget.tag_add("sel", "1.0", "end-1c")
        return "break"  # prevent default behavior
    
    def _reset_console(self) -> None:
        """
        Clear the console and insert header. Called once during initializing

        Returns
        -------
        None
        """
        self.console.config(state=tk.NORMAL)
        self.console.delete("1.0", tk.END)
        self.console.insert(tk.END, self.console_header)
        self.console.config(state=tk.DISABLED)

    def _console_printline(self, text: str, mode: str, addline: bool) -> None:
        """
        Print a single line of text to console

        Parameters
        ----------
        text : str
            The line to be printed
        mode : str
            The visual appearance of this line. Right now the options are:
                "success" = green background
                "error" = red background
                "warning" = yellow background
                "print" = blue text
            These are defined when the console is created in layout.py
        addline : bool
            Whether to add a line of dashes behind the printed line. This is 
            for aesthetics.

        Returns
        -------
        None
        """
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, f"{text}")

        # Add highlighting to line, from line_num.0 to line_num.end
        line_num = self.console.index("end-1c").split(".")[0]
        self.console.tag_add(mode, f"{line_num}.0", f"{line_num}.end")

        # Add the unhighlighted dashed line if needed
        if addline:
            self.console.insert(tk.END, f"\n{self.console_hline}")
        
        # Add newline, scroll to newest line and disable editing again
        self.console.insert(tk.END, "\n")
        self.console.see(tk.END) 
        self.console.config(state=tk.DISABLED)

    def _compile(self) -> None:
        """
        Compile the xgc script to basic G-code.

        This function can be called via Ctrl/Command + Enter in xgc editor.
        This is the uppermost layer in compilation error handling. It calls
        xgc_to_gcode with the necessary arguments, and prints the correct
        error info to the console. As of now, the error analysis framework can
        detect which line the error occured, and whether it occured before or
        after the exec() step.

        Returns
        -------
        None
        """
        # Read xgc script and clear output
        self.result_output.config(state=tk.NORMAL)
        self.result_output.delete("1.0", tk.END)
        xgc_script = self.xgc_editor.get("1.0", "end-1c")

        # Create gcode header if enabled. Time is formatted as YYYY-MM-DD
        # HH:MM:SS
        if self.settings["transpiler"]["add_header"]:
            gcode = (
                f"; Compiled by GRoller v{self.groller_ver} on "
                f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n"
                "; Source File: "
                f"{self.settings["file_io"]["current_file"]}\n\n"
            )
        else:
            gcode = ""

        try:
            # Compile the xgc script into gcode
            gcode += xgc_to_gcode(xgc_script, self.settings["transpiler"])
        except Exception as e: 
            # Compilation failed for some reason
            # Get the traceback object and check if the exception occured
            # before or after the exec() stage.
            traceback_str = traceback.format_exc()
            # print(traceback_str)
            match = re.search( # This line only shows up in exec() layer
                r"File \"<string>\", line (\d+)",
                traceback_str
            )
            if match: # Error occured in exec()
                line_number = int(match.group(1)) # Capture error location
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
            self.result_output.insert(tk.END, gcode)
        finally:
            # Disable result_output again and trigger linenumber redraw
            self.result_output.config(state=tk.DISABLED)
            self.result_output_linenums.redraw()
        return "break" # Prevent default behavior of Ctrl+Enter, which is Enter

    def _read_settings(self):
        """
        Read settings from settings.json in the same directory

        This is the first function called during app init. As the app couldn't
        function if settings.json can't be found, this function will show 
        messagebox then abort if that happens.

        Returns
        -------
        None
        """
        try:
            with self.settings_json_path.open("r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except Exception as e:
            # Reliably ensures the messagebox is on top of the main window 
            self.root.lift() 
            self.root.withdraw()
            # Show a messagebox with the error info
            tk.messagebox.showerror(
                "Error loading settings.json",
                f"{e.__class__.__name__}: {e}",
                parent=self.root
            )
            # Close app
            self.root.destroy()
            sys.exit(0)
    
    def _load_settings(self):
        """
        Process the settings that was just read in

        This function is called right after _read_settings() and basically 
        "deploys" the setting parameters if necessary. Right now, it sets up 
        the app's internal font system using user-defined font sizes before the
        main window is generated.

        Returns
        -------
        None
        """
        # 1.
        # Set up the internal font system according to user preference
        # These are then used by UI all over the app
        self._label_font = font.nametofont("TkDefaultFont").copy()
        self._label_font.configure(
            size=self.settings["ui"]["fontsize"]["label"]
        )
        self._editor_font = font.nametofont("TkFixedFont").copy()
        self._editor_font.configure(
            size=self.settings["ui"]["fontsize"]["editor"]
        )
        self._console_font = font.nametofont("TkFixedFont").copy()
        self._console_font.configure(
            size=self.settings["ui"]["fontsize"]["console"]
        )
        self._paragraph_font = font.nametofont("TkDefaultFont").copy()
        self._paragraph_font.configure(
            size=self.settings["ui"]["fontsize"]["paragraph"]
        )
        self._button_font = font.nametofont("TkDefaultFont").copy()
        self._button_font.configure(
            size=self.settings["ui"]["fontsize"]["button"]
        )

    def _save_settings_to_json(self):
        """
        Write the current state of settings object to settings.json

        This function is called whenever the settings is changed by user, so
        it persists after the app closes.

        Returns
        -------
        None
        """
        with self.settings_json_path.open("w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)