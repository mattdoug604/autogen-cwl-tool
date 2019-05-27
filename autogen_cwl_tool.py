#!/usr/bin/env python

import re
import sys

from copy import deepcopy
from subprocess import Popen, PIPE, STDOUT

import yaml


__version__ = "0.0.1"

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

SHEBANG = "#!/usr/bin/env cwl-runner"
CWLVERSION = "v1.0"

DEFAULT_ARG = {
    "id": None,
    "type": None,
    "doc": "",
    "inputBinding": {"position": 0, "prefix": None},
}

# 1+ word(s) preceeded by ['-', '--'] and sep by ['-', '.', '_'] and not preceeded by another letter
RE_PREFIX = r"(?<![a-z]|[A-Z])\-{1,2}[\w\-\.\?\@_]+"
# match one of TYPE_LIST in the string
RE_TYPE = r"\b(?:" + "|".join([re.escape(i) for i in TYPE_LIST]) + r")\b"


def read_help_cmd(cmd):
    """
    Notes:
        - can't use error codes b/c some programs 'fail' to display help text
    """

    help_text = []
    cmd = [i for i in cmd if i not in ('-h', '--help')] + ["-h"]

    p = Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
    for line in p.stdout:
        line = line.rstrip()
        if len(line) > 0:
            help_text.append(line)

    return help_text


def normalize_type(type_range):

    type_range = type_range.lower().strip()
    if type_range in TYPE_LIST:
        return TYPE_LIST[type_range]

    return None


def match_position(line, regex):

    result = []

    match = re.search(regex, line)
    while match:
        match_str = match.group()
        match_spn = match.span()
        match_dct = {match_spn: match_str}
        result.append(match_dct)
        match = re.search(regex, line)

    return result


def mask_ranges(line, ranges, maskchar=" "):

    mask = ""
    x = 0
    for a, b in ranges:
        mask += line[x:a]
        mask += maskchar * len(range(a, b))
        x = b
    mask += line[x:]

    return mask


def check_prefix_positions(line, ranges, mask=[]):

    accept = []
    i = 0
    last = 0

    line = mask_ranges(line, mask)

    while True:
        if i == len(ranges):
            break
        irange = ranges[i]
        start, end = irange
        substr = line[last:start]
        match = re.search(r"\w+", substr)
        i += 1
        if not match:
            accept.append(irange)
            last = end
        else:
            pass

    return accept


def format_id(inputs, prfx_str, escape=99):

    exist_id = [i["inputBinding"]["prefix"] for i in inputs]
    base_id = prfx_str.strip("-").replace("-", "_")
    arg_id = base_id
    n = 2
    while base_id in exist_id:
        arg_id = base_id + "{}".format(n)
        n += 1
        if n > escape:
            raise ValueError("No unique id for input: '{}'".format(prfx_str))

    return arg_id


def get_inputs(help_text):

    inputs = []
    arg = {}

    # munge each line in the help text
    for line in help_text:

        # init parameters
        prfx_range = []
        type_range = []
        docs_range = []

        # match argument prefix(es)
        for match in re.finditer(RE_PREFIX, line):
            prfx_range.append(match.span())
            # debug_line(line, prfx_range[-1], 'prfx')
        # match recognized input type
        for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
            type_range.append(match.span())
            # debug_line(line, match.span(), 'type')

        # sanity check: prefixes are not seperated by words (excluding "input type" words)
        prfx_range = check_prefix_positions(line, prfx_range, type_range)
        # sanity check: prefixes are not seperated by words (excluding "input type" words)
        type_range = check_prefix_positions(line, type_range, prfx_range)
        # sanity check: doc string starts after prefix/type
        ranges = [0] + [i[1] for i in prfx_range + type_range]
        docs_range = [(max(ranges), None)]

        # extract subtrings
        prfx_list = [line[i:j] for i, j in prfx_range]
        type_list = [line[i:j] for i, j in type_range]
        docs_list = [line[i:j] for i, j in docs_range]

        # select result
        prfx_str = (
            None
            if not prfx_list
            else sorted([i for i in prfx_list], key=len, reverse=True)[0].strip()
        )
        type_str = None if not type_list else type_list[0].strip()
        docs_str = docs_list[0]

        # sanity check: exclude doc lines starting at index 0, reset arg
        if docs_range[0][0] == 0 and docs_str[0] != " ":
            if arg:
                inputs.append(arg)
            arg = {}
            continue

        # assemble each input
        if prfx_range:
            if arg:
                inputs.append(arg)
            arg = deepcopy(DEFAULT_ARG)
            arg["id"] = format_id(inputs, prfx_str)
            arg["inputBinding"]["prefix"] = prfx_str
        if arg:
            if type_str:
                arg["type"] = normalize_type(type_str)
            if docs_str:
                arg["doc"] += docs_str.strip() + ["" if docs_str[-1] == "-" else " "][0]
    if arg:
        inputs.append(arg)

    # post-process inputs
    for arg in inputs:

        if not arg["id"]:
            raise ValueError("No id for input: {}".format(arg))

        if not arg["type"]:
            arg["type"] = "Any"  # ask for input?

        if not arg["doc"]:
            print("Warning: no docstring for input: '{}'".format(arg["id"]))
        else:
            arg["doc"] = arg["doc"].strip()

        if not arg["inputBinding"]["prefix"]:
            raise ValueError("No prefix defined for input: '{}'".format(arg["id"]))

    return inputs


def output_as_yaml(cmd, inputs, outputs=[]):

    with open('tool.yaml', 'w') as fh:
        print(SHEBANG, file=fh)
        print('class: CommandLineTool', file=fh)
        print('cwlVersion: {}'.format(CWLVERSION), file=fh)
        yaml.dump({'baseCommand': cmd}, fh, default_flow_style=False)
        print('', file=fh)
        yaml.dump({'inputs': inputs}, fh, default_flow_style=False)
        print('', file=fh)
        yaml.dump({'outputs': outputs}, fh, default_flow_style=False)


if __name__ == "__main__":

    # strip any help command line arguments
    cmd = [i for i in sys.argv[1:] if i not in ('-h', '--help')]
    help_text = read_help_cmd(cmd)

    intputs = get_inputs(help_text)
    output_as_yaml(cmd, intputs)
