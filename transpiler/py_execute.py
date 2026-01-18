"""
py_execute.py

This module contains functions that executes a Python script from xgc_to_py.py
which then yields the final G-code. Together with xgc_to_py.py, the two modules
form a source-to-source compiler (transpiler) from XGC to G-code.

Author: Wei-Hsu Lin
"""

import math

"""
global variables of this module, never used elsewhere. Their only purpose is
to be accessible to the G-code functions even inside exec() since a function's 
global is determined at definition, not at execution.
"""

# A dict that records the current state of the machine.
machine_state = {
    "polar_mode": {
        "enabled": False,      # Turned on by G16 and off by G15
        "cx": 0.0,             # Set by G16
        "cy": 0.0              # Set by G16
    },
    "canned_cycle": {
        "mode": "",
        "params": {}
    },
    "unit": "mm",              # Set by G20/G21, No real use for now.
    "positioning": "absolute", # Set by G90/G91. No real use for now.
    "spindle_state": "off",    # Set by M03/M05. No real use for now.
    "spindle_rpm": 0,          # Set by M03/M05. No real use for now.
    "feedrate_mode": "normal", # Set by G93/G94. No real use for now.
    "arc_plane": "XY"          # Set by G17/G18/G19. No real use for now.
}
app = None                 # The app instance, added upon GUI initialization
exec_result = ""           # The compiled G-code!

def python_to_gcode(python_code) -> str:
    global exec_result, exec_ns
    exec_result = "" # clear old result 
    exec(python_code, exec_ns)
    return exec_result

def grant_gui_access(my_app_instance: tk.Tk) -> None:
    # Called during the init of UI so it's injected to this module's global
    global app
    app = my_app_instance

def frange(start: int | float, stop: int | float, step: int | float) -> list:
    """
    Simple, float-compatible version of the famous range()

    A simple function that works the same as the range(). Inclusive to start
    value but exclusive to stop value. Can detect infinite loops and raise 
    error accordingly.

    Args:
        start (float): Starting value
        stop (float): Stopping value
        step (float): Step size, must be nonzero

    Returns:
        list: The list to iterate over

    Raises:
        ValueError: Loop step cannot be zero
        ValueError: Infinite loop detected
    """
    if step == 0:
        raise ValueError("Loop step must be non-zero")
    result, i = [], start
    if step > 0 and stop > start:
        while i < stop and not math.isclose(i, stop):
            result.append(i)
            i += step
    elif step < 0 and start > stop:
        while i > stop and not math.isclose(i, stop):
            result.append(i)
            i += step
    else:
        # Infinite loop: i would moves away from stop indefinitely
        raise ValueError("frange(): Infinite loop detected")
    return result

def console_print(input: int | float | str) -> None:
    """
    print() but to the GUI console

    Basically a print() that's redirectly to the GUI console.  Trivial data 
    types only. Outputs of this function are light blue colored.

    Parameters
    ----------
    input : int, float or str
        The thing to be printed to the console.

    Returns
    -------
    None
        This function does not return anything.
    """
    if not isinstance(input, (int, float, str)):
        raise TypeError("console_print: Input is not a number or string")
    app._console_printline(input, "print", False)

def G00(**kwargs: dict) -> None:
    """
    Rapid Linear motion

    Basically the same command as G01 but goes at the fastest allowed speed. 

    Parameters
    ----------
    kwargs : dict
        The parameters passed in. Should be a subset of X, Y and Z. If more
        than three axis are involved then also A, B and C. In polar mode, X and
        Y are interpreted as radius and angle(degrees).

    Returns
    -------
    None
        This function does not return anything.
    
    Raises
    ------
    ValueError
        Unexpected parameters are present

    See Also
    --------
    G01 : Linear motion
    """
    global machine_state, exec_result

    # Check if unexpected G00 parameters are present, if so raise exception.
    illegal = set(kwargs) - {"X", "Y", "Z", "A", "B", "C"}
    if illegal:
        raise ValueError(f"G00 contains unexpected parameter(s): {illegal}")

    # Calculate the X(radius) and Y(angle) into actual X and Y
    if machine_state["polar_mode"]["enabled"]:
        """
        If both X(radius) and Y(angle) is provided, attempt to convert to 
        Cartesian. If only one is provided raise an exception. If neither is 
        provided then it's a pure Z movement and let it pass. Tl;DR: User has 
        to provide either just Z or X, Y and Z.
        """
        if {"X", "Y"} <= set(kwargs):
            # Polar -> Cartesian.
            r, theta = kwargs["X"], kwargs["Y"]
            cx = machine_state["polar_mode"]["cx"]
            cy = machine_state["polar_mode"]["cy"]
            x = cx + r * math.cos(math.radians(theta))
            y = cy + r * math.sin(math.radians(theta))
            kwargs["X"], kwargs["Y"] = x, y
        elif ("X" in kwargs) and ("Y" not in kwargs):
            raise ValueError("G00 (polar mode) needs argument Y")
        elif ("X" not in kwargs) and ("Y" in kwargs):
            raise ValueError("G00 (polar mode) needs argument X")

    gcode_line = f"G00 {" ".join(f"{k}{v}" for k, v in kwargs.items())}\n"
    exec_result += gcode_line

def G01(**kwargs: dict) -> None:
    """
    Linear motion

    One of, if not THE most important G-code command. 

    Parameters
    ----------
    kwargs : dict
        The parameters passed in. Should be a subset of X, Y, Z and F. If more
        than three axis are involved then also A, B and C. In polar mode, X and
        Y are interpreted as radius and angle(degrees).

    Returns
    -------
    None
        This function does not return anything.

    Raises
    ------
    ValueError
        Unexpected parameters are present

    See Also
    --------
    G00 : Rapid linear motion
    """
    global machine_state, exec_result

    # Check if unexpected G01 parameters are present, if so raise exception.
    illegal = set(kwargs) - {"X", "Y", "Z", "A", "B", "C", "F"}
    if illegal:
        raise ValueError(f"G01 contains unexpected parameter(s): {illegal}")

    # Calculate the X(radius) and Y(angle) into actual X and Y
    if machine_state["polar_mode"]["enabled"]:
        """
        If both X(radius) and Y(angle) is provided, attempt to convert to 
        Cartesian. If only one is provided raise an exception. If neither is 
        provided then it's a pure Z movement and let it pass. Tl;DR: User has 
        to provide either just Z or X, Y and Z.
        """
        if {"X", "Y"} <= set(kwargs):
            # Polar -> Cartesian
            r, theta = kwargs["X"], kwargs["Y"]
            cx = machine_state["polar_mode"]["cx"]
            cy = machine_state["polar_mode"]["cy"]
            x = cx + r * math.cos(math.radians(theta))
            y = cy + r * math.sin(math.radians(theta))
            kwargs["X"], kwargs["Y"] = x, y
        elif ("X" in kwargs) and ("Y" not in kwargs):
            raise ValueError("G01 (polar mode) needs an extra argument: Y")
        elif ("X" not in kwargs) and ("Y" in kwargs):
            raise ValueError("G01 (polar mode) needs an extra argument: X")

    gcode_line = f"G01 {" ".join(f"{k}{v}" for k, v in kwargs.items())}\n"
    exec_result += gcode_line

def G02(**kwargs: dict) -> None:
    """
    Clockwise arc

    This command is surprisingly non-trivial and complicated when implemented.
    Therefore, this function only checks if unexpected parameters show up, and
    nothing else. The operator is responsible to make sure it behaves as one
    intended.

    Parameters
    ----------
    kwargs : dict
        The parameters passed in. One expects some subset of X, Y, Z, I, J, K,
        R, F

    Returns
    -------
    None
        This function does not return anything.
    
    Raises
    ------
    ValueError
        Unexpected parameters are present

    See Also
    --------
    G03 : Counterclockwise arc
    """
    global machine_state, exec_result

    # Check if unexpected G02 parameters are present, if so raise exception.
    illegal = set(kwargs) - {"X", "Y", "Z", "I", "J", "K", "R", "F"}
    if illegal:
        raise ValueError(f"G02 contains unexpected parameter(s): {illegal}")

    gcode_line = f"G02 {" ".join(f"{k}{v}" for k, v in kwargs.items())}\n"
    exec_result += gcode_line

def G03(**kwargs: dict) -> None:
    """
    Counterclockwise arc

    This command is surprisingly non-trivial and complicated when implemented.
    Therefore, this function only checks if unexpected parameters show up, and
    nothing else. The operator is responsible to make sure it behaves as one
    intended.

    Parameters
    ----------
    kwargs : dict
        The parameters passed in. One expects some subset of X, Y, Z, I, J, K,
        R, F

    Returns
    -------
    None
        This function does not return anything.

    Raises
    ------
    ValueError
        Unexpected parameters are present

    See Also
    --------
    G02 : Clockwise arc
    """
    global machine_state, exec_result

    # Check if unexpected G03 parameters are present, if so raise exception.
    illegal = set(kwargs) - {"X", "Y", "Z", "I", "J", "K", "R", "F"}
    if illegal:
        raise ValueError(f"G03 contains unexpected parameter(s): {illegal}")

    gcode_line = f"G03 {" ".join(f"{k}{v}" for k, v in kwargs.items())}\n"
    exec_result += gcode_line

def G04(P: int | float) -> None:
    """
    Dwell for P time. Positive time = seconds and negative time = milliseconds.

    The behavior of G04 varies across different controllers. In XGC, one 
    always specifiy the time in P and use positive/negative to specify unit.
    This function then checks the user specified G04 flavor in settings and
    output the correct format for the machine. Default flavor is RS-274, i.e.,
    P<seconds>.

    Parameters
    ----------
    P : int or float
        Dwell time. Positive time = seconds and negative time = milliseconds.

    Returns
    -------
    None
        This function does not return anything.
    """
    global exec_result

    match app.settings["transpiler"]["g04-style"]:
        case "RS-274": # Output is in P<seconds>
            exec_result += f"G04 P{P}\n" if P >= 0 else f"G04 P{-P/1000}\n"
                
def G15(is_line_end: bool) -> None:
    """
    Leave polar coordinate mode. It does not print itself to output.

    Parameters
    ----------
    is_line_end : bool
        A parameter passed in from preprocessor. Not relevant for this function 
        since it is not meant to be present in the final G-code.

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G16 : Turn on polar coordinate mode and optionally set origin.
    """
    global machine_state

    machine_state["polar_mode"]["enabled"] = False

def G16(X: int | float, Y: int | float) -> None:
    """
    Enter polar coordinate mode.

    Enter polar coordinate mode and optionally set the origin. It does not 
    print itself to output.

    Parameters
    ----------
    X : int or float
        X position of the origin
    Y : int or float
        Y position of the origin

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G15 : Turn off polar coordinate mode and return to Cartesian.
    G01 : Linear motion

    Notes
    -----
    As of now, the only supported command inside this mode is G01 and the only
    thing it does is convert (R,A) to (X,Y).
    """
    global machine_state

    machine_state["polar_mode"]["enabled"] = True
    machine_state["polar_mode"]["cx"] = X
    machine_state["polar_mode"]["cy"] = Y

def G17(is_line_end: bool) -> None:
    """
    Set G02/G03 arc plane to XY. This is implicit in 99.9% of use cases.

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G18 : Set arc plane to XZ
    G19 : Set arc plane to YZ
    """
    global machine_state, exec_result

    machine_state["arc_plane"] = "XY"
    exec_result += "G17\n" if is_line_end else "G17 "

def G18(is_line_end: bool) -> None:
    """
    Set G02/G03 arc plane to XZ.

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G17 : Set arc plane to XY
    G19 : Set arc plane to YZ
    """
    global machine_state, exec_result

    machine_state["arc_plane"] = "XZ"
    exec_result += "G18\n" if is_line_end else "G18 "

def G19(is_line_end: bool) -> None:
    """
    Set G02/G03 arc plane to YZ.

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G17 : Set arc plane to XY
    G18 : Set arc plane to XZ
    """
    global machine_state, exec_result

    machine_state["arc_plane"] = "YZ"
    exec_result += "G19\n" if is_line_end else "G19 "

def G20(is_line_end: bool) -> None:
    """
    Set unit to inches. No effect in this program

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = "\\n", False = " ". This is becuase
        G20 is parameterless and often show up in a single line with others.
        Ex: G17 G90 G20 

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G21 : Set unit to millimeters.
    """
    global machine_state, exec_result

    machine_state["unit"] = "in"
    if is_line_end:
        exec_result += "G20\n"
    else:
        exec_result += "G20 "

def G21(is_line_end: bool) -> None:
    """
    Set unit to millimeters. No effect in this program

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = "\\n", False = " ". This is becuase
        G21 is parameterless and often show up in a single line with others.
        Ex: G17 G90 G21 

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G20 : Set unit to inches.
    """
    global machine_state, exec_result

    machine_state["unit"] = "mm"
    if is_line_end:
        exec_result += "G21\n"
    else:
        exec_result += "G21 "

def canned_cycle_xy(X: int | float, Y: int | float) -> None:
    global machine_state, exec_result
    params = machine_state["canned_cycle"]["parameters"]
    match machine_state["canned_cycle"]["mode"]:
        case "": # Not in canned cycle mode, raise error
            raise SyntaxError(
                "Canned cycle line (X,Y) appeared outside canned cycle"
            )
        case "G81.1": # G81.1: Simple drilling cycle, enhanced version
            G00(X=X, Y=Y)  # Rapid move above hole
            # Repeat if L is specified, otherwise just do it once
            i = 0
            while i < (params["L"] if "L" in params else 1):
                G01(Z=params["Z"], F=params["F"]) # Go down at specified F
                if "P" in params:                 # Dwell if specified P
                    G04(P=params["P"])
                G00(Z=params["R"])                # Rapid retract
                i += 1

def G80(is_line_end: bool) -> None:
    """
    Leave canned cycle mode. It does not print itself to output.

    Parameters
    ----------
    is_line_end : bool
        A parameter passed in from preprocessor. Not relevant for this function 
        since it is not meant to be present in the final G-code.

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G81_1 : Basic drilling cycle
    """
    global machine_state

    machine_state["canned_cycle"]["mode"] = "" # Serves as False
    machine_state["canned_cycle"]["parameters"] = {} # Empty it out

def G81_1(**kwargs: dict) -> None:
    global machine_state

    illegal = set(kwargs) - {"Z", "R", "F", "X", "Y", "L", "P", "D", "A"}
    if illegal:
        raise ValueError(f"G81.1 contains unexpected parameter(s): {illegal}")
    missing_required = {"Z", "R", "F", "X", "Y"} - set(kwargs)
    if missing_required:
        raise ValueError(
            f"G81.1 necessary parameter(s) missing: {missing_required}"
        )
    if ("D" in set(kwargs)) ^ ("A" in set(kwargs)): # XOR
        raise ValueError(
            "G81.1 parameters \"D\" and \"A\" must either provided together, "
            "or not provided at all."
        )
    # Check complete, no issues detected, proceed
    machine_state["canned_cycle"]["mode"] = "G81.1"

    # Pass all of kwargs except X and Y to canned cycle parameter global.
    X, Y = kwargs.pop("X"), kwargs.pop("Y")
    machine_state["canned_cycle"]["parameters"] = kwargs
    
    # Call canned cycle on the first (X,Y) coordinate
    canned_cycle_xy(X=X, Y=Y)

def G90(is_line_end: bool) -> None:
    """
    Set to absolute positioning mode. No effect in this program

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ". This is becuase
        G90 is parameterless and often show up in a single line with others.
        Ex: G17 G90 G21 

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G91 : Set to incremental positioning mode.
    """
    global machine_state, exec_result

    machine_state["positioning"] = "absolute"
    if is_line_end:
        exec_result += "G90\n"
    else:
        exec_result += "G90 "

def G91(is_line_end: bool) -> None:
    """
    Set to incremental positioning mode. No effect in this program

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ". This is becuase
        G91 is parameterless and often show up in a single line with others.
        Ex: G17 G91 G21 

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G90 : Set to absolute positioning mode.
    """
    global machine_state, exec_result

    machine_state["positioning"] = "incremental"
    exec_result += "G91\n" if is_line_end else "G91 "

def G93(is_line_end: bool) -> None:
    """
    Set feedrate mode to inverse.

    While this is defined since the dawn of G-code (RS-274), I highly doubt 
    anyone using this program would need it.

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G94 : Set feedrate mode back to normal (units per minute).
    """
    global machine_state, exec_result

    machine_state["feedrate_mode"] = "inverse"
    exec_result += "G93\n" if is_line_end else "G93 "

def G94(is_line_end: bool) -> None:
    """
    Set feedrate mode to normal (units per minute)

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    G93 : Set feedrate mode to inverse.
    """
    global machine_state, exec_result

    machine_state["feedrate_mode"] = "normal"
    exec_result += "G94\n" if is_line_end else "G94 "

def M03(S: int) -> None:
    """
    Start spindle clockwise at S RPM

    Parameters
    ----------
    S : int
        The spindle speed. This is  dependent on stock material, cutter 
        material, your machine setup, etc.

    Returns
    -------
    None
        This function does not return anything.

    Raises
    ------
    TypeError
        S must be an integer
    
    See Also
    --------
    M05 : Stop spindle.
    """
    global machine_state, exec_result

    if not isinstance(S, int):
        raise TypeError("M03 spindle RPM must be an integer")
    machine_state["spindle_state"] = "on"
    machine_state["spindle_rpm"] = S
    exec_result += f"M03 S{S}\n"

def M05(is_line_end: bool) -> None:
    """
    Stop Spindle

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    See Also
    --------
    M03 : Start spindle clockwise.
    """
    global machine_state, exec_result

    machine_state["spindle_RPM"] = 0
    machine_state["spindle_state"] = "off"
    if is_line_end:
        exec_result += "M05\n"
    else:
        exec_result += "M05 "

def M30(is_line_end: bool) -> None:
    """
    End of program.

    Parameters
    ----------
    is_line_end : bool
        What to insert after itself. True = \\n, False = " ".

    Returns
    -------
    None
        This function does not return anything.

    Notes
    -----
    Check out the exact use case of M30 here:
    https://www.cnccookbook.com/program-stop-and-end-g-codes-m00-m01-m02-and-m30/
    """
    global exec_result

    exec_result += "M05\n" if is_line_end else "M05 "

# Namespace of exec()
exec_ns = {
    # "Bans" all dangerous features. One can technically still access them
    # through convoluted jail breaks, but TL;DR this is good enough for the 
    # purpose of this program. See [] for more details.
    "__builtins__": {}, 

    # Math functions from math module
    "cos": lambda x: math.cos(math.radians(x)), # Degree based trig
    "sin": lambda x: math.sin(math.radians(x)),
    "tan": lambda x: math.tan(math.radians(x)),
    "PI": math.pi,
    "E": math.e,
    "abs": math.fabs,
    "sqrt": math.sqrt,
    "pow": math.pow,
    "log": math.log,
    "exp": math.exp,

    # Other functions passed in
    "round": round,
    "frange": frange,
    "console_print": console_print,

    # The G-code functions, core of this Python hack
    "G00": G00,
    "G01": G01,
    "G02": G02,
    "G03": G03,
    "G04": G04,
    "G15": G15,
    "G16": G16,
    "G17": G17,
    "G18": G18,
    "G19": G19,
    "G20": G20,
    "G21": G21,
    # Implementation of canned cycle, not directly called by user
    "canned_cycle_xy": canned_cycle_xy, 
    "G80": G80,
    "G81_1": G81_1,
    "G90": G90,
    "G91": G91,
    "G93": G93,
    "G94": G94,
    "M03": M03,
    "M05": M05
}