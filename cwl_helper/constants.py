import re

__program__ = "cwl-helper"
__version__ = "0.0.3"

# Primitive types: string, int, long, float, double, null
# Complex types: array, record
# Special types: File, Directory, Any
TYPE_LIST = {
    "any": "Any",
    "array": "array",
    "bool": "boolean",
    "boolean": "boolean",
    "dir": "Directory",
    "directory": "Directory",
    "double": "double",
    "enum": "enum",
    "file": "File",
    "float": "float",
    "int": "int",
    "integer": "int",
    "list": "array",
    "long": "long",
    "none": "null",
    "null": "null",
    "record": "record",
    "str": "string",
    "string": "string",
}

# match a substring that looks like a list
RE_LIST = r"\{.*?\,.*?\}|\[.*?\,.*?\]"
# 1+ word(s) preceeded by ['-', '--'] and sep by ['-', '.', '_'] and not preceeded by another letter
RE_PREFIX = r"(?<![a-z]|[A-Z]|[0-9])\-{1,2}[a-zA-Z0-9\-\.\?\@_]+"
# match large whitespaces (e.g. preceeding a column)
RE_SPACE = r"\s{3,}(?=[a-zA-Z0-9]+)"
# match one of TYPE_LIST in the string
RE_TYPE = r"\b(?:" + "|".join([re.escape(i) for i in TYPE_LIST]) + r")\b"