"""
layout.py

This module creates all the layout of the app outside the menubar.
Only one function is exposed here: create_layout()

Author: Wei-Hsu Lin
"""

import math, sys
import tkinter as tk
from tkinter import font
from tkinter.scrolledtext import ScrolledText
from lib.tklinenums import TkLineNumbers

def create_layout(app: tk.Tk) -> None:
    # _configure_root_grid(app, True)
    _create_text_editors(app)
    _create_console(app)

def _place_grid(widget: tk.Widget, size: tuple, 
    position: tuple, grid: tuple = (32,18)) -> None:
    """
    A simple wrapper around tk.place() to place on a virtual "grid"

    Parameters
    ----------
    widget : tk.Widget
        The widget to be place()'d
    size : tuple
        A tuple with 2 elements: size = (width, height)
    position : tuple
        A tuple with 3 elements: size = (x, y, anchor)
    grid : tuple
        A tuple with 2 elements: grid = (cols, rows). It is defaulted to
        (32, 18), the virtual "grid" I use on the root, since most widgets
        that call this function is place()'d on the root. Widgets not in the
        root override this on a case-by-case basis.

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    tk.place() : The actual working function 
    """
    #
    border = widget.cget("borderwidth")
    widget.place(
        relx = position[0] / grid[0], # All relative values between 0.0 and 1.0
        rely = position[1] / grid[1],
        relwidth = size[0] / grid[0],
        relheight = size[1] / grid[1],
        anchor = position[2]
    )


def _configure_root_grid(app: tk.Tk, show: bool) -> None:
    """
    Creates the root grid in app that every other widgets uses.

    I choose to design a constant width/height grid first then
    arranging the widgets on it. Not the default behavior of
    grid() but I prefer this.

    Args:
        app (tk.Tk): The app instance
        show (bool): Whether to display the grid visually, only on
            during development

    Returns:
        None
    """
    rows, cols = 18, 32 # Enough for this app
    for r in range(rows):
        app.grid_rowconfigure(r, weight=1, uniform="root_grid")
    for c in range(cols):
        app.grid_columnconfigure(c, weight=1, uniform="root_grid")
    # Display the grid visually (only on during development)
    if show:
        colors = ["lightblue", "lightgreen"]
        for r in range(rows):
            for c in range(cols):
                frame = tk.Frame(
                    app,
                    bg=colors[(r + c) % 2],  # checkerboard pattern
                    highlightbackground="black",
                    highlightthickness=0, # visible grid lines
                )
                frame.grid(row=r, column=c, sticky="nsew")
    
            
def _create_text_editors(app: MainApp) -> None:
    """
    Creates the two textareas: xgc_editor and result_output

    These two textareas warrant their own function since they
    have extra features on them, i.e., the line number display
    and the scroll bars

    Args:
        app (MainApp): The app instance

    Returns:
        None
    """

    # Create Labels
    app.xgc_editor_label = tk.Label(
        app.root, 
        text="Extended G-code (XGC) Script",
        font=app._label_font
    )
    _place_grid(app.xgc_editor_label, (12, 1), (10, 1, "nw"))
    app.result_output_label = tk.Label(
        app.root,
        text="Compiled G-code",
        font=app._label_font
    )
    _place_grid(app.result_output_label, (8, 1), (23, 1, "nw"))

    # Create frames that host the line number widget, textarea and scroll bar
    app.xgc_editor_frame = tk.Frame(app.root)
    _place_grid(app.xgc_editor_frame, (12,15), (10, 2, "nw"))
    app.xgc_editor_frame.columnconfigure(0, weight=0)  # Line number
    app.xgc_editor_frame.columnconfigure(1, weight=1)  # Textarea (horiz fill)
    app.xgc_editor_frame.columnconfigure(2, weight=0)  # Scrollbar
    app.xgc_editor_frame.rowconfigure(0, weight=1)     # All fill vertically

    app.result_output_frame = tk.Frame(app.root)
    _place_grid(app.result_output_frame, (8,15), (23, 2, "nw"))
    app.result_output_frame.columnconfigure(0, weight=0)
    app.result_output_frame.columnconfigure(1, weight=1)
    app.result_output_frame.columnconfigure(2, weight=0)
    app.result_output_frame.rowconfigure(0, weight=1)

    # Line Number | Textarea | Scrollbar. Arranged using grid() to change
    # width dynamically

    # Create scrollbar inside respective frames
    app.xgc_editor_scrollbar = tk.Scrollbar(app.xgc_editor_frame)
    app.result_output_scrollbar = tk.Scrollbar(app.result_output_frame)

    # Create textarea inside respective frames. Their yscrollcommand
    # connection wtih scrollbar is handled together on linenumber widget init
    app.xgc_editor = tk.Text(
        app.xgc_editor_frame,
        # yscrollcommand=app.xgc_editor_scrollbar.set,
        width=1, height=1, undo=True, font=app._editor_font
    )
    app.result_output = tk.Text(
        app.result_output_frame, state = tk.DISABLED,
        # yscrollcommand=app.result_output_scrollbar.set,
        width=1, height=1, font=app._editor_font 
    ) # One shouldn't edit the output

    # Add hotkeys to xgc_editor: Ctrl+Enter = Compile and Tab = User-defined
    # space count
    app.xgc_editor.bind("<Control-Return>", lambda e: app._compile(), add=True)
    app.xgc_editor.bind("<Command-Return>", lambda e: app._compile(), add=True)

    def tab_to_spaces(event):
        spaces = " " * app.settings["ui"]["tab_spaces"]  # User defined
        event.widget.insert("insert", spaces)
        return "break"
    
    app.xgc_editor.bind("<Tab>", tab_to_spaces, add=True)
    
    # Create linenumber widget, bind to textarea and intialize
    app.xgc_editor_linenums = TkLineNumbers(
        app.xgc_editor_frame,
        app.xgc_editor,
        app.xgc_editor_scrollbar,
        justify="right",
        colors=("#2197db", "#ffffff")
    )
    # Redraw the line numbers when the text widget contents are modified,
    # either by editing (xgc_editor) or scrolling (both)
    for update_event in ["<KeyRelease>", "<MouseWheel>"]:
        app.xgc_editor.bind(
            update_event,
            lambda event: app.root.after_idle(app.xgc_editor_linenums.redraw),
            add=True
        )
    app.result_output_linenums = TkLineNumbers(
        app.result_output_frame,
        app.result_output,
        app.result_output_scrollbar,
        justify="right",
        colors=("#2197db", "#ffffff")
    )
    app.result_output.bind(
        "<MouseWheel>",
        lambda event: app.root.after_idle(app.result_output_linenums.redraw),
        add=True
    )        

    # Finish the other direction of of text-scrollbar connection
    app.xgc_editor_scrollbar.config(
        command=lambda *args:
        (app.xgc_editor.yview(*args), app.xgc_editor_linenums.redraw())
    )
    app.result_output_scrollbar.config(
        command=lambda *args:
        (app.result_output.yview(*args), app.result_output_linenums.redraw())
    )

    # Arrange everything via grid()
    app.xgc_editor_linenums.grid(row=0, column=0, sticky="ns")
    app.xgc_editor.grid(row=0, column=1, sticky="nsew")
    app.xgc_editor_scrollbar.grid(row=0, column=2, sticky="ns")
    app.result_output_linenums.grid(row=0, column=0, sticky="ns")
    app.result_output.grid(row=0, column=1, sticky="nsew")
    app.result_output_scrollbar.grid(row=0, column=2, sticky="ns")

def _create_console(app: MainApp) -> None:
    """
    Create the compilation status console and associated widgets

    Create the compilation status console, its label, clear button and compile
    button. The console's header is also computed here.

    Parameters
    ----------
    app : MainApp
        The app instance

    Returns
    -------
    None
        This function does not return anything.

    Notes
    -----
    """
    # Create console label and console
    app.console_label = tk.Label(
        app.root, text="Compilation Console", font=app._label_font
    )
    _place_grid(app.console_label, (8, 1), (1, 7, "nw"))

    app.console = ScrolledText(
        app.root, state=tk.DISABLED, wrap=tk.WORD, font=app._console_font
    )
    _place_grid(app.console, (8, 8), (1, 8, "nw"))

    # Highlighting tags, colors chosen by ChatGPT: I simply asked for a soft
    # and light set of green, orange and red, all with HSL lightness close to
    # 75%.
    app.console.tag_config("success", background="#a7dca7") # green
    app.console.tag_config("error", background="#f28b82") # red
    app.console.tag_config("warning", background="#ffea80") # yellow
    # Blue text, same nice blue as line widget
    app.console.tag_config("print", foreground="#2197db") 


    # Measure the console width in characters, then make the adequate console
    # header that will be inserted after every _reset_console()
    app.root.update_idletasks() # Make sure the size of console is rendered
    console_char_width = ( # Rounded down and play safe by minus 2
        app.console.winfo_width() // app._console_font.measure("0") - 2
    )
    ch_first_line = (
        f"GRoller {app.groller_ver} | Python {sys.version.split()[0]}"
    )
    app.console_hline = "-" * console_char_width
    app.console_header = (
        f"{ch_first_line.center(console_char_width)}\n{app.console_hline}\n"
    )

    # Create the two buttons
    app.console_clear_btn = tk.Button(
        app.root, text="Clear", 
        command=app._reset_console, font=app._button_font
    )
    _place_grid(app.console_clear_btn, (2, 1), (1, 16, "nw"))

    app.console_compile_btn = tk.Button(
        app.root, text="Compile",
        command=app._compile, font=app._button_font
    )
    _place_grid(app.console_compile_btn, (4, 1), (5, 16, "nw"))

    # Run _reset_console() once during initialization
    app._reset_console()

    
