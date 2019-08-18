#!/usr/bin/env python3

"""
TODO:
* match 'type' in the format: <type>
"""

import argparse
import logging
import re
import sys
from collections import defaultdict

from cwlgen import CommandLineTool

from .arg import Arg
from .common import in_bounds, list_is_bools
from .constants import (
    CWL_VERSION,
    RE_PREFIX,
    RE_TYPE,
    RE_LIST,
    RE_SPACE,
    TYPE_LIST,
    __program__,
    __version__,
)
from .convert import arg_to_cwlgen


def check_for_columns(text, threshold=0.1):
    """
    Search for the start positions that of regex matches that occur frequently.
    Assumes several things:
    * prefix comes first, type comes before doc string
    * type may not be consistently placed
    * required args come before optional ones
    * an argument does not contain blank lines
    """

    min_prfx = 0
    min_type = 0
    min_spce = 0

    prfx_ranges = defaultdict(int)
    type_ranges = defaultdict(int)
    spce_ranges = defaultdict(int)

    # iterate once through the text to try and find columns
    for line in text:
        logging.debug("Reading: {}".format(line))

        # match argument prefix(es)
        for match in re.finditer(RE_PREFIX, line):
            start = match.span()[0]
            match = match.group(0).strip()
            prfx_ranges[start] += 1
        # match recognized input type (e.g "FILE", "string", "LIST")
        for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
            start = match.span()[0]
            match = match.group(0).strip()
            type_ranges[start] += 1
        # match multiple whitespaces, indicative of a gap between columns
        for match in re.finditer(RE_SPACE, line):
            end = match.span()[1]
            match = match.group(0).strip()
            spce_ranges[end] += 1

    # find the most common prefix postions
    total_prfx = sum(prfx_ranges.values())
    filter_prfx = {
        k: v for k, v in prfx_ranges.items() if v / total_prfx > threshold
    }
    min_prfx = min_prfx if not filter_prfx else min(filter_prfx)
    logging.debug("Filter prefix start = {}".format(min_prfx))

    total_type = sum(type_ranges.values())
    filter_type = {
        k: v
        for k, v in type_ranges.items()
        if v / total_type > threshold and k > min_prfx
    }
    min_type = min_type if not filter_type else min(filter_type)
    logging.debug("Filter type start = {}".format(min_type))

    total_spce = sum(spce_ranges.values())
    filter_spce = {
        k: v
        for k, v in spce_ranges.items()
        if v / total_spce > threshold and k > max(min_prfx, min_type)
    }
    min_spce = min_spce if not filter_spce else min(filter_spce)
    logging.debug("Filter docstring start = {}".format(min_spce))

    return min_prfx, min_type, min_spce


def parse_inputs(text, min_prfx=0, min_type=0, min_spce=0):

    inputs = []
    arg = None

    # iterate again through the text to match values
    for n, line in enumerate(text):
        prfx_matches = []
        type_matches = []
        spce_matches = []
        match, start = None, None
        last = 0
        prfxm, typem, spacem = None, None, None

        logging.debug("-" * 80)
        if not line:
            logging.debug("Skipping blank line number {}".format(n))
        else:
            logging.debug("Reading line number {}:".format(n))
            logging.debug(line)

            # match argument prefix(es)
            matchl = list(re.finditer(RE_PREFIX, line))
            # all matches should be within pre-defined bounds
            matchl = [i for i in matchl if in_bounds(i.span()[0], min_prfx, min_spce)]
            # everything before the first match should be whitespace
            if matchl:
                start = matchl[0].span()[0]
                group = matchl[0].group(0)
                upstr = line[:start]
                if start > 0 and not upstr.isspace():
                    logging.debug(
                        "Ignore 'prefix' '{}' b/c upstream is not space: '{}'".format(
                            group, upstr
                        )
                    )
                else:
                    for match in matchl:
                        start, end = match.span()
                        group = match.group(0).strip()
                        if in_bounds(start, min_prfx, min_spce):
                            prfx_matches.append(group)
                            last = max(last, end)
                            logging.debug(
                                "match 'prefix' at position {}: '{}'".format(
                                    start, group
                                )
                            )
                            # match symbols that go with the prefix
                            # TODO: full implement symbol matching
                            logging.debug("> {} {}".format(line[end:], line[end]))
                            if line[end] == "=":
                                logging.debug("Matching line: {}".format(line[end+1:]))
                                match_symbol = list(re.finditer(RE_LIST, line[end+1:]))
                                if match_symbol:
                                    logging.debug("Match: {} with {}".format(group, match_symbol[0].group()))


            # match recognized input type (e.g "FILE", "string", "LIST")
            for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
                start, end = match.span()
                group = match.group(0).strip()
                if in_bounds(start, max(min_prfx, min_type, last), min_spce):
                    type_matches.append(group)
                    last = max(last, end)
                    logging.debug(
                        "match 'type' at position {}: '{}'".format(start, group)
                    )

            # match multiple whitespaces, indicative of a gap between columns
            matchl = list(re.finditer(RE_SPACE, line))
            if matchl:
                for match in matchl:
                    start = match.span()[1]
                    group = line[start:]
                    if in_bounds(start, min_spce):
                        spce_matches.append(group)
                        logging.debug(
                            "match 'docstring' at position {}: '{}'".format(
                                start, group
                            )
                        )
                    # relax the position requirement if not sharing the line with a
                    # prefix
                    elif not prfx_matches:
                        spce_matches.append(group)
                        logging.debug(
                            "loose match 'docstring' at position {}: '{}'".format(
                                start, group
                            )
                        )
            # if the docstring is not preceeded by 3+ whitespaces, assume it starts at
            # 'min_spce' if not overlapping a prefix
            else:
                if len(line) > min_spce and line[min_spce - 1].isspace():
                    group = line[min_spce:]
                    spce_matches.append(group)
                    logging.debug(
                        "assume 'docstring' at position {}: '{}'".format(
                            min_spce, group
                        )
                    )

        # assume parameters do not have blank lines
        if not prfx_matches and not type_matches and not spce_matches:
            if arg:
                inputs.append(arg)
            arg = None
            continue

        # select longest prefix
        if prfx_matches:
            prfxm = sorted(prfx_matches, key=len)[-1]
            logging.debug("Select 'prefix': '{}'".format(prfxm))
        # select first matching type
        if type_matches:
            typem = type_matches[0]
            logging.debug("Select 'type': '{}'".format(typem))
        # select last docstring match
        if spce_matches:
            spacem = spce_matches[-1]
            logging.debug("Select 'docstring': '{}'".format(spacem))

        # assemble argument params that may be spread over multiple lines
        # if we hit a new prefix, assume its the start of the next argument
        # TODO: select the more "complete" args if a prefix was caught mistakenly?
        if prfxm:
            if arg:
                inputs.append(arg)
            arg = Arg(prfxm)
        if arg and typem:
            arg.intype = typem
        if arg and spacem:
            arg.append_doc(spacem)

    for arg in inputs:
        logging.debug("Arg: {}'".format(arg))

    return inputs


def post_process(inputs):

    filter_list = []

    for arg in inputs:
        prfxm = arg.prefix
        typem = arg.intype.lower()
        docm = arg.doc
        logging.debug("-" * 80)
        logging.debug("Post-process arg: '{}'".format(prfxm))

        # try to coerce type into a valid CWL type
        # assume params without a type are boolean
        if typem and typem in TYPE_LIST:
            new_type = TYPE_LIST[typem]
        else:
            new_type = "boolean"
        arg.intype = new_type
        logging.debug("Coercing type '{}' to '{}'".format(typem, new_type))

        # try to identify choices; indicate an enum
        choices = list(re.finditer(RE_LIST, docm))
        if choices:
            choices = re.sub(r"\{|\}|\[|\]|\,", "", choices[-1].group()).split(" ")
            logging.debug("Matched list '{}' in '{}'".format(choices, docm))
            # TODO: properly interpret a CWL list
            if list_is_bools(choices):
                arg.type = "boolean"
                logging.debug("Interpret list as 'boolean'")
            else:
                arg.intype = "string"
                logging.debug("Interpret list as 'string'")

        filter_list.append(arg)

    for arg in filter_list:
        logging.debug("Arg: {}'".format(arg))

    return filter_list


def arg_parse():

    parser = argparse.ArgumentParser(add_help=False)

    opt_tool = parser.add_argument_group("tool information")
    opt_tool.add_argument("-t", "--tool-id", default="tool_id", help="specify tool_id")
    opt_tool.add_argument(
        "-b", "--base-cmd", default="command", help="specify base_command"
    )
    opt_tool.add_argument(
        "-d", "--tool-doc", default="docstring", help="specify the tool docstring"
    )
    opt = parser.add_argument_group("optional arguments")
    opt.add_argument("-i", "--input", help="input is a text file (default: stdin)")
    opt.add_argument("-o", "--output", help="output to file (default: stdout)")
    opt.add_argument(
        "-c",
        "--columns",
        type=int,
        nargs=3,
        help="""manually specify the start postion of 'prefix', 'type', and 
        'docstring' (e.g. -c 0 12 30). Set value(s) to -1 to ignore.""",
    )
    opt.add_argument(
        "--no-columns",
        action="store_true",
        help="do not try to auto-detect columns (use '-c' instead)",
    )
    opt.add_argument(
        "--version",
        action="version",
        version="{} v{}".format(__program__, __version__),
        help="print the version and exit",
    )
    opt.add_argument(
        "-v", "--verbose", action="store_true", help="print extra information"
    )
    opt.add_argument("-h", "--help", action="help", help="print this message and exit")

    return parser.parse_args()


def main():
    """
    Entrypoint for cwl-helper
    """
    args = arg_parse()

    logger = logging.getLogger()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.input:
        with open(args.input, "r") as fh:
            text = fh.readlines()
    else:
        text = sys.stdin.readlines()

    print(text)

    if not args.columns and not args.no_columns:
        columns = check_for_columns(text)
    if args.columns:
        columns = args.columns

    inputs = parse_inputs(text, *columns)
    filter_list = post_process(inputs)

    cwl_args = [arg_to_cwlgen(i) for i in filter_list]

    tool_object = CommandLineTool(
        tool_id=args.tool_id,
        base_command=args.base_cmd,
        doc=args.tool_doc,
        cwl_version=CWL_VERSION,
    )
    tool_object.inputs = cwl_args
    tool_object.outputs = []

    # An input and output header are needed to run a CWL tool. However, cwlgen does not
    # output these by if they are empty lists.
    if args.output:
        tool_object.export(args.output)
        with open(args.output, "a") as fh:
            if not cwl_args:
                print("inputs: []", file=fh)
            print("outputs: []", file=fh)
    else:
        tool_object.export()
        if not cwl_args:
            print("inputs: []")
        print("outputs: []")


if __name__ == "__main__":
    main()
