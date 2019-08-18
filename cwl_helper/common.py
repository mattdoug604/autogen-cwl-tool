import re
from subprocess import Popen, PIPE, STDOUT
from string import punctuation


def in_bounds(value, lower=None, upper=None):
    """
    Check if value is in a given range where the upper and/or lower bounds can be 
    undefined.
    """
    if lower and value < lower:
        return False
    if upper and value > upper:
        return False
    return True


def list_is_bools(str_list):
    """Check if all the values in a list are literally 'true' or 'false'"""

    for i in str_list:
        if not i.lower() in ("true", "false"):
            return False
    return True


def id_from_cmd(cmd):
    """
    Convert a shell command to an ID string by:
    * replacing punction with underscores
    * replacing uppercase letters with lowercase equivalent preceeded by an underscore
    * replacing multiple underscores in a row with one underscore
    """

    old = punctuation + " "
    new = "_" * len(old)
    tool_id = cmd.translate(str.maketrans(old, new))
    tool_id = re.sub("(?<!^)(?=[A-Z])", "_", tool_id).lower()
    tool_id = re.sub("_{2,}", "_", tool_id)

    return tool_id
