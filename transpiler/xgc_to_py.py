"""
xgc_to_py.py

This module contains functions that converts the extended G-code (XGC) script 
into a Python script, whose execution directly yields the final G-code. 
Together with py_execute.py, the two modules form a source-to-source compiler 
(transpiler) from XGC to G-code.

Author: Wei-Hsu Lin
"""

import re, ast
from .py_execute import python_to_gcode

def xgc_to_gcode(xgc_content: str, val_precision: tuple) -> str:
    python_code = xgc_to_python(xgc_strip(xgc_content))
    crude_gcode = python_to_gcode(python_code)
    final_gcode = round_gcode(crude_gcode, val_precision)
    return final_gcode

def xgc_strip(xgc_script: str) -> str:
    """
    Strip the xgc script of comments, [] syntax sugar and empty lines.

    The only type of comments that are allowed in xgc, and the ones that this
    function strips, are semicolon ; ones, where both inline and standalone 
    versions are allowed. Parantheses () are prohibited since functions also 
    use them (ex: X[10*cos(i)])

    Args:
        xgc_script (str): The xgc script grabbed straight from the editor

    Returns:
        str: The stripped xgc script
    """
    # Strip all ; to line end
    result: str = re.sub(r"[ \t]*;.*", "", xgc_script) 

    # Remove empty/whitespace only lines that the user made or created during
    # previous stripping. tk.Text always uses \n.
    result = "\n".join(
        line for line in result.splitlines() if line.strip()
        )

    # Strip the [] syntax sugar, those are just for human readability
    result = result.replace("[", "").replace("]", "")

    return result
    
def xgc_to_python(xgc_script: str) -> str:
    """
    Convert a single line of xgc to its corresponding function

    Converts a G/M command with parameters (ex: G01 X10 Y5 Z1) to a function
    of the same name: G01(X=10, Y=5, Z=1), which will be used in exec() to
    hack Python. Also works for parameters with variables. Note: This function 
    requires no gaps between parameter and value, and a gap between the value 
    and next parameter.

    Parameters
    ----------
    xgc_line : str
        The line of xgc script to convert

    Returns
    -------
    str
        The converted function (still one line) to be exec()ed in next step

    Notes
    -----
    The whole function is encapsulated in a try-except. If exception is raised
    at any step, then it attaches the line number to its error message and
    propagates upward, eventually displayed in the GUI status console.
    """
    python_code: str = "" 
    # Work over the script line by line. Deal with each line on a case by case
    # basis as shown below
    line_no = 0 # Keep track of line number for error report
    # Set of supported G-code commands that take no input
    paramaterless_commands: set = {
        "G15", "G17", "G18", "G19", "G20", "G21", "G90", 
        "G91", "G93", "G94","M05", "M30"
    }
    try:
        for line in xgc_script.splitlines(): 
            line_no += 1
            stripped_line = line.strip()
            # Split line into tokens, used throughout this function. Example:
            # "G01 X10 Y[5+i] Z3 " -> ["G01", "X10", "Y[5+i]", "Z3"]. 
            tokens = stripped_line.split()
            keys = [token[0] for token in tokens]
            
            # "Real" python code and variable declaration: don't touch at all. 
            # Note that indentation of nested for loop is preserved. Right now 
            # I detect by assuming that Python code starts with a lowercase 
            # character, but I don't like it. 
            if (stripped_line[0].islower() or
                _is_variable_declaration(stripped_line)):
                python_code += f"{line}\n"
                continue

            # If the line consists of only X and/or Y, then it is a line in a 
            # canned cycle and is dealt with here. 
            
            # Case 1: Both X and Y are present. Regex matches:
            # X[num or expression][some space]Y[num or expression]
            elif set(keys) == {"X", "Y"}:
                line = re.sub(
                    r"X([^\s]+)\s+Y([^\s]+)",
                    r"canned_cycle(X=\1, Y=\2)",
                    line
                )
                python_code += f"{line}\n"
                continue

            # Case 2: Only X is present. Regex matches: X[num or expression]
            elif set(keys) == {"X"}:
                line = re.sub(
                    r"X([^\s]+)",
                    r"canned_cycle(X=\1)",
                    line
                )
                python_code += f"{line}\n"
                continue

            # Case 3: Only Y is present. Regex matches: Y[num or expression]
            elif set(keys) == {"Y"}:
                line = re.sub(
                    r"Y([^\s]+)",
                    r"canned_cycle(Y=\1)",
                    line
                )
                python_code += f"{line}\n"
                continue
                
            # At this point the line is a normal G-code line (i.e., starts with
            # a command) unless user straight up inputs nonsense. If the line 
            # consists of only parameterless G/M command (e.g., safety starting
            # line or mode change), then it is dealt here. The effects of True
            # and False are shown in py_execute.py.

            elif set(tokens) <= paramaterless_commands: # subset detection
                # Actually legit, proceed
                python_code += f"{"(False)\n".join(tokens)}(True)\n"
                continue
            
            # Finally, the most common scenario: The line is a G-code line with
            # parameters (ex: G01 X10 Y5 Z1). A dedicated function has been 
            # made for this case.
            
            python_code += f"{_xgc_line_to_func(line)}\n"
        return python_code

    except Exception as e:
        # Attach line number info to error message, then re-raise
        e.args = (f"Line {line_no}: {e.args[0]}",)
        raise

def _is_variable_declaration(s: str) -> bool:
    """
    Checks if a string represents a simple Pythonic varaible assignment

    Using ast, this function returns True for strings that follow the rule
    <name> (= <name>)* = <any expression>. Example:
    x = 42      --> (True)  | y = x + 1   --> (True)
    x = y = 42  --> (True)  | x, y = 42, 137  --> (False)
    42 = x      --> (False) | x == 42 (False)

    Args:
        s (str): The string to be checked

    Returns:
        bool: True if the string satisfies the condition, False otherwise.
    """
    try:
        node = ast.parse(s)
    except SyntaxError:
        return False

    # Must be a single assignment statement
    return (
        len(node.body) == 1
        and isinstance(node.body[0], ast.Assign)
        and all(isinstance(t, ast.Name) for t in node.body[0].targets)
    )

def _xgc_line_to_func(xgc_line: str) -> str:
    """
    Convert a single line of xgc to its corresponding function

    Converts a G/M command with parameters (ex: G01 X10 Y5 Z1) to a function
    of the same name: G01(X=10, Y=5, Z=1), which will be used in exec() to
    hack Python. Also works for parameters with variables. Note: This function 
    requires no gaps between parameter and value, and a gap between the value 
    and next parameter.

    Parameters
    ----------
    xgc_line : str
        The line of xgc script to convert

    Returns
    -------
    str
        The converted function (still one line) to be exec()ed in next step
    """
    # Keep track of leading space to add back at the end. This is necessary 
    # for lines in for loops as Python uses indentation for scoping.
    leading_space = re.split(r"[GM]", xgc_line, maxsplit=1)[0]
    
    # Get command (ex: "G01") and parameter string (ex: "X10 Y5 Z1")
    command, param_str = xgc_line.split(None, maxsplit=1)

    # Extract key-value pairs using regex. param_list is a list of tuples.
    param_list: list = re.findall(r"([A-Z])([^\s]+)", param_str)

    # Join the results back together and create the function as a string
    param_str = ", ".join(f"{k}={v}" for k, v in param_list)
    return f"{leading_space}{command}({param_str})"

def round_gcode(crude_gcode: str, max_precision: tuple):

    position_prec, angular_prec = max_precision
    position_pattern = r"([XYZ])(-?\d+(?:\.\d+)?)"
    angular_pattern = r"([ABC])(-?\d+(?:\.\d+)?)"
    def round_val(match, prec):
        k, v = match.group(1), float(match.group(2))
        return f"{k}{v:.{prec}f}"
    
    middle_gcode = re.sub(position_pattern, 
        lambda m: round_val(m, position_prec), crude_gcode)
    final_gcode = re.sub(angular_pattern, 
        lambda m: round_val(m, angular_prec), middle_gcode)

    return final_gcode

if __name__ == "__main__":
    script = """
    radius = 3
    path = radius+0.2

    G21
    G04 P1
    for i in frange(1,4,1):
        for j in frange(1,4,1):
            G01 X[i] Y[j] Z[radius*cos(i)]
    """

    print(xgc_to_gcode(script))