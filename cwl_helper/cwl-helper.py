#!/usr/bin/env python

"""
TODO:
* match 'type' in the format: <type>
"""

import logging

logging.basicConfig(format="[%(levelname)s] %(message)s")

import argparse
import re
import sys
from collections import defaultdict, namedtuple
from subprocess import Popen, PIPE, STDOUT

from cwlgen import CommandInputParameter, CommandLineBinding, CommandLineTool

from constants import (
    __program__,
    __version__,
    TYPE_LIST,
    RE_PREFIX,
    RE_TYPE,
    RE_LIST,
    RE_SPACE,
)


class Arg:
    def __init__(self, prefix, arg_type=None, doc=None):
        self.__prefix = prefix
        self.__type = arg_type
        self.__doc = doc

    def __str__(self):
        return "prefix:'{}' type:'{}' doc:'{}'".format(
            self.__prefix, self.__type, self.__doc
        )

    def get_prefix(self):
        return self.__prefix or ""

    def get_type(self):
        return self.__type or ""

    def get_doc(self):
        return self.__doc or ""

    def get_id(self):
        return self.__prefix.strip("-").replace("-", "_")

    def set_prefix(self, prefix): 
        self.__prefix = prefix.strip()

    def set_type(self, arg_type):
        self.__type = arg_type.strip()

    def set_doc(self, doc):
        self.__doc = doc.strip()

    def append_doc(self, doc):
        doc = doc.strip()
        if not self.__doc:
            self.set_doc(doc)
        else:
            if self.__doc[-1] == "-":
                self.__doc += doc
            else:
                self.__doc += " " + doc


def in_bounds(position, lower=None, upper=None):

    if lower and position < lower:
        return False
    if upper and position > upper:
        return False
    return True


def list_is_bools(value):

    for i in value:
        if not i.lower() in ("true", "false"):
            return False
    return True


def check_for_columns(text, threshold=0.1):
    """
    Notes
        * assume prefix comes before, type comes before doc string
        * assume type may not be consistently placed
        * assume required args come before optional ones
        * assume an argument does not contain blank lines
    """

    min_prfx = 0
    min_type = 0
    min_spce = 0

    prfx_ranges = defaultdict(list)
    type_ranges = defaultdict(list)
    spce_ranges = defaultdict(list)

    # iterate once through the text to try and find columns
    for line in text:

        # match argument prefix(es)
        for match in re.finditer(RE_PREFIX, line):
            start = match.span()[0]
            match = match.group(0).strip()
            prfx_ranges[start].append(line)
        # match recognized input type (e.g "FILE", "string", "LIST")
        for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
            start = match.span()[0]
            match = match.group(0).strip()
            type_ranges[start].append(line)
        # match multiple whitespaces, indicative of a gap between columns
        for match in re.finditer(RE_SPACE, line):
            end = match.span()[1]
            match = match.group(0).strip()
            spce_ranges[end].append(line)

    # find the most common prefix postions
    total_prfx = sum([len(v) for v in prfx_ranges.values()])
    filter_prfx = {
        k: v for k, v in prfx_ranges.items() if len(v) / total_prfx > threshold
    }
    min_prfx = min_prfx if not filter_prfx else min(filter_prfx)
    logging.debug("Filter prefix start = {}".format(min_prfx))

    total_type = sum([len(v) for v in type_ranges.values()])
    filter_type = {
        k: v
        for k, v in type_ranges.items()
        if len(v) / total_type > threshold and k > min_prfx
    }
    min_type = min_type if not filter_type else min(filter_type)
    logging.debug("Filter type start = {}".format(min_type))

    total_spce = sum([len(v) for v in spce_ranges.values()])
    filter_spce = {
        k: v
        for k, v in spce_ranges.items()
        if len(v) / total_spce > threshold and k > max(min_prfx, min_type)
    }
    min_spce = min_spce if not filter_spce else min(filter_spce)
    logging.debug("Filter docstring start = {}".format(min_spce))

    return min_prfx, min_type, min_spce


def iter_text(text, columns):

    min_prfx, min_type, min_spce = columns

    # iterate again through the text to match values
    for n, line in enumerate(text):
        prfx_matches = []
        type_matches = []
        spce_matches = []
        match, start = None, None
        last = 0

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
                match = matchl[0].group(0)
                upstr = line[:start]
                if start > 0 and not upstr.isspace():
                    logging.debug(
                        "Ignore 'prefix' '{}' b/c upstream is not space: '{}'".format(
                            match, upstr
                        )
                    )
                else:
                    for match in matchl:
                        start, end = match.span()
                        match = match.group(0).strip()
                        if in_bounds(start, min_prfx, min_spce):
                            prfx_matches.append(match)
                            last = max(last, end)
                            logging.debug(
                                "match 'prefix' at position {}: '{}'".format(
                                    start, match
                                )
                            )
                            # match symbols that go with the prefix
                            # TODO: full implement symbol matching
                            logging.info("> {} {}".format(line[end:], line[end]))
                            if line[end] == "=":
                                logging.info("Matching line: {}".format(line[end+1:]))
                                match_symbol = list(re.finditer(RE_LIST, line[end+1:]))
                                if match_symbol:
                                    logging.info("Match: {} with {}".format(match, match_symbol[0].group()))


            # match recognized input type (e.g "FILE", "string", "LIST")
            for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
                start, end = match.span()
                match = match.group(0).strip()
                if in_bounds(start, max(min_prfx, min_type, last), min_spce):
                    type_matches.append(match)
                    last = max(last, end)
                    logging.debug(
                        "match 'type' at position {}: '{}'".format(start, match)
                    )

            # match multiple whitespaces, indicative of a gap between columns
            matchl = list(re.finditer(RE_SPACE, line))
            if matchl:
                for match in matchl:
                    start = match.span()[1]
                    match = line[start:]
                    if in_bounds(start, min_spce):
                        spce_matches.append(match)
                        logging.debug(
                            "match 'docstring' at position {}: '{}'".format(
                                start, match
                            )
                        )
                    # relax the position requirement if not sharing the line with a
                    # prefix
                    elif not prfx_matches:
                        spce_matches.append(match)
                        logging.debug(
                            "loose match 'docstring' at position {}: '{}'".format(
                                start, match
                            )
                        )
            # if the docstring is not preceeded by 3+ whitespaces, assume it starts at
            # 'min_spce' if not overlapping a prefix
            else:
                if len(line) > min_spce and line[min_spce - 1].isspace():
                    match = line[min_spce:]
                    spce_matches.append(match)
                    logging.debug(
                        "assume 'docstring' at position {}: '{}'".format(
                            min_spce, match
                        )
                    )

        yield prfx_matches, type_matches, spce_matches


def build_args(text, columns):

    arg_list = []
    arg = None

    for prfx_matches, type_matches, spce_matches in iter_text(text, columns):
        prfxm, typem, spacem = None, None, None

        # assume parameters do not have blank lines
        if not prfx_matches and not type_matches and not spce_matches:
            if arg:
                arg_list.append(arg)
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
                arg_list.append(arg)
            arg = Arg(prfxm)
        if arg and typem:
            arg.set_type(typem)
        if arg and spacem:
            arg.append_doc(spacem)

    for arg in arg_list:
        logging.debug("Arg: {}'".format(arg))

    return arg_list


def post_process(arg_list):

    filter_list = []

    for arg in arg_list:
        prfxm = arg.get_prefix()
        typem = arg.get_type().lower()
        docm = arg.get_doc()
        logging.debug("-" * 80)
        logging.debug("Post-process arg: '{}'".format(prfxm))

        # try to coerce type into a valid CWL type
        # assume params without a type are boolean
        if typem and typem in TYPE_LIST:
            new_type = TYPE_LIST[typem]
        else:
            new_type = "boolean"
        arg.set_type(new_type)
        logging.debug("Coercing type '{}' to '{}'".format(typem, new_type))

        # try to identify choices; indicate an enum
        choices = list(re.finditer(RE_LIST, docm))
        if choices:
            choices = re.sub(r"\{|\}|\[|\]|\,", "", choices[-1].group()).split(" ")
            logging.debug("Matched list '{}' in '{}'".format(choices, docm))
            # TODO: properly interpret a CWL list
            if list_is_bools(choices):
                arg.set_type("boolean")
                logging.debug("Interpret list as 'boolean'")
            else:
                arg.set_type("string")
                logging.debug("Interpret list as 'string'")

        filter_list.append(arg)

    for arg in filter_list:
        logging.debug("Arg: {}'".format(arg))

    return filter_list


def convert_to_cwlgen(arg_list):

    cwl_args = []

    for arg in arg_list:
        prfxm = arg.get_prefix()
        typem = arg.get_type()
        docm = arg.get_doc()
        logging.debug("-" * 80)
        logging.debug("Converting arg: '{}'".format(prfxm))

        cwl_binding = CommandLineBinding(prefix=prfxm, position=0)
        cwl_input = CommandInputParameter(
            arg.get_id(), param_type=typem, input_binding=cwl_binding, doc=docm
        )
        cwl_args.append(cwl_input)

    return cwl_args


# def call_help_cmd(cmd):

#     text = []
#     proc = Popen(
#         cmd, stdout=PIPE, stderr=PIPE
#     )
#     for source in (proc.stdout, proc.stderr):
#         for line in source.readlines():
#             line = line.decode("utf-8")
#             if line:
#                 text.append(line)
#     return text


def arg_parse():

    parser = argparse.ArgumentParser(add_help=False)

    req = parser.add_argument_group("required arguments")
    req.add_argument(
        "-i", "--input", required=True, help="a text file containing the output of a help command"
    )

    opt = parser.add_argument_group("tool information")
    opt.add_argument("-t", "--tool-id", help="specify tool_id")
    opt.add_argument("-b", "--base-cmd", help="specify base_command")
    opt.add_argument("-d", "--tool-doc", help="specify the tool docstring")

    opt = parser.add_argument_group("optional arguments")
    opt.add_argument("-o", "--output", help="output to file")
    opt.add_argument(
        "-c",
        "--columns",
        type=int,
        nargs=3,
        help="""manually specify the start postion of 'prefix', 'type', and 
        'docstring' (e.g. -c 0 12 30). Set value(s) to -1 to ignore.""",
    )
    opt.add_argument(
        "--no-columns", action="store_true", help="do not try to auto-detect columns"
    )
    opt.add_argument("--verbose", action="store_true", help="print extra information")
    opt.add_argument("-h", "--help", action="help", help="print this message and exit")

    return parser.parse_args()


if __name__ == "__main__":

    args = arg_parse()

    logger = logging.getLogger()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logging.info("Reading from file: {}".format(args.input))
    with open(args.input, "r") as fh:
        text = fh.readlines()

    if not args.columns and not args.no_columns:
        columns = check_for_columns(text)
    if args.columns:
        columns = args.columns
    arg_list = build_args(text, columns)
    filter_list = post_process(arg_list)

    cwl_args = convert_to_cwlgen(filter_list)

    tool_object = CommandLineTool(
        tool_id="test_id",
        base_command="test",
        doc="this is a test tool",
        cwl_version="v1.0",
    )
    tool_object.inputs = cwl_args
    tool_object.outputs = []
    tool_object.export()
