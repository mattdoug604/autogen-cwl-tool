#!/usr/bin/env python

# common imports
import argparse
import logging
import re
import sys
from collections import defaultdict, namedtuple
from copy import deepcopy
from subprocess import Popen, PIPE, STDOUT

# external imports
from cwlgen import CommandInputParameter, CommandLineBinding, CommandLineTool
from constants import __program__, __version__, TYPE_LIST, RE_PREFIX, RE_TYPE, RE_LIST

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)


# --- Class(es) ------------------------------------------------------------- #
class HelpText:
    def __init__(self, command, help_param="--help"):

        self.command = command
        self.help_param = help_param
        self.text = []
        # self.id_dict = defaultdict(int)
        self.ids = set()

    def read(self):
        """
        Method for reading the help text output by a program to stdout/stderr. Ignores blank lines
        Notes:
            - can't use error codes b/c some programs 'fail' to display help text
        """

        if self.help_param:
            self.command = self.command + [self.help_param]

        p = Popen(self.command, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        self.text = [i.rstrip() for i in p.stdout]

    def parse(self):

        inputs = []
        param = None

        for rprfx, rtype, rdocs in self._iter_text():
            if rprfx and self._has_id(rprfx.str):
                continue
            if not any((rprfx, rtype, rdocs)):
                if param:
                    inputs.append(param)
                param = None
                continue
            # sanity check: exclude doc lines starting at index 0, reset param
            if rdocs and rdocs.str and rdocs.start == 0 and rdocs.str[0] != " ":
                if param:
                    inputs.append(param)
                param = None
                continue

            # assemble each input
            if rprfx:
                if param:
                    inputs.append(param)
                param_id = self._get_id(rprfx.str)
                if not param_id:  # skip "--"
                    continue
                param_binding = CommandLineBinding(prefix=rprfx.str, position=0)
                param = CommandInputParameter(param_id, input_binding=param_binding)
            if param:
                if rtype:
                    param.type = self._normalize_type(rtype.str)
                if rdocs:
                    param.doc = self._concat_doc(param.doc, rdocs.str)
        if param:
            inputs.append(param)

        # post-process inputs
        for param in inputs:

            # all inputs should have an id
            if not param.id:
                raise ValueError("No id for input: {}".format(param))

            # try to auto-detect 'enum'
            choices = [i for i in re.finditer(RE_LIST, param.doc) if i]
            if choices:
                choices = re.sub(r"\{|\}|\[|\]|\,", "", choices[-1].group()).split(" ")
                if list_is_bools(choices):
                    param.type = "boolean"
                else:
                    # param.type = {"type": "enum", "symbols": choices}  # cwlgen doesn't seem to support enum, need workaround
                    param.type = "string"

            # default to boolean if no type is specified
            if not param.type:
                param.type = "boolean"

            # check doc strings
            if not param.doc:
                print("Warning: no docstring for input: '{}'".format(param.id))
            else:
                param.doc = param.doc.strip()
                # assume if "required" is in the doc string, it is required
                if not 'required' in param.doc.lower():
                    if isinstance(param.type, dict):
                        param.type['type'] += "?"
                    else:
                        param.type += "?"

            # all inputs should have a prefix
            if not param.inputBinding.prefix:
                raise ValueError(
                    "No prefix defined for input: '{}'".format(param.id)
                )

        return inputs

    def _check_pos(self, line, ranges, mask=[]):

        accept = []
        i = 0
        last = 0

        line = self._mask_ranges(line, mask)

        while True:
            if i >= len(ranges):
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

    def _concat_doc(self, a, b):

        if a:
            return a.strip() + ["" if a[-1] == "-" else " "][0] + b.strip()
        else:
            return b.strip()

    # def _get_unique_id(self, prfx_str):

    #     base_id = prfx_str.strip("-").replace("-", "_").replace(":", "_")
    #     suffix = self.id_dict[base_id]
    #     self.id_dict[base_id] += 1
    #     if suffix:
    #         return base_id + str(suffix)
    #     else:
    #         return base_id

    def _has_id(self, prfx_str):

        param_id = prfx_str.strip("-").replace("-", "_").replace(":", "_")
        return param_id in self.ids
    
    def _get_id(self, prfx_str):

        param_id = prfx_str.strip("-").replace("-", "_").replace(":", "_")
        self.ids.add(param_id)
        return param_id
        

    def _iter_text(self):

        Match = namedtuple('Match', ['str', 'start', 'end'])

        # munge each line in the help text
        for line in self.text:

            # init parameters
            prfx_ranges = []
            type_ranges = []
            docs_ranges = []

            # skip blank lines
            if not line:
                yield None, None, None

            # match argument prefix(es)
            for match in re.finditer(RE_PREFIX, line):
                prfx_ranges.append(match.span())
            # match recognized input type
            for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
                type_ranges.append(match.span())

            # sanity check: prefixes are not seperated by words (excluding "input type" words)
            # prfx_ranges = self._check_pos(line, prfx_ranges, type_ranges)
            # sanity check: types are not seperated by words (excluding input prefixes)
            type_ranges = self._check_pos(line, type_ranges, prfx_ranges)
            # sanity check: doc string starts after prefix/type
            docs_ranges = [(max([0] + [i[1] for i in prfx_ranges + type_ranges]), None)]

            # extract subtrings
            prfx_list = sorted([line[i:j] for i, j in prfx_ranges], key=len)
            type_list = sorted([line[i:j] for i, j in type_ranges])
            docs_list = sorted([line[i:j] for i, j in docs_ranges])

            # select results
            prfx_str = None if not prfx_list else prfx_list[-1].strip()
            type_str = None if not type_list else type_list[0].strip()
            docs_str = None if not docs_list else docs_list[0].rstrip()

            rprfx = None if not prfx_list else Match(prfx_str, *prfx_ranges[-1])
            rtype = None if not type_list else Match(type_str, *type_ranges[0])
            rdocs = None if not docs_list else Match(docs_str, *docs_ranges[0])

            yield rprfx, rtype, rdocs

    def _mask_ranges(self, line, ranges, maskchar=" "):

        mask = ""
        x = 0
        for a, b in ranges:
            mask += line[x:a]
            mask += maskchar * len(range(a, b))
            x = b
        mask += line[x:]

        return mask

    def _normalize_type(self, type_str):

        type_str = type_str.lower()
        if type_str in TYPE_LIST:
            return TYPE_LIST[type_str]

        return None


# --- General function(s) --------------------------------------------------- #
def list_is_bools(value):

    for i in value:
        if not i.lower() in ("true", "false"):
            return False
    return True


def parse_args():
    """
    Method for parsing commandline arguments.
    """

    parser = argparse.ArgumentParser(
        description="Create a bare-bones CWL tool for the specified command."
    )
    parser.add_argument("output", help="output file")
    parser.add_argument("command", nargs="+", help="shell command")
    parser.add_argument(
        "-p", 
        "--param",
        type=str,
        default="--help", 
        help="param used to print help text"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="{} v{}".format(__program__, __version__),
        help="show the program version and and exit",
    )

    args = parser.parse_args()

    # strip any common help parameters
    args.command = [i for i in args.command if i not in ("-h", "--help")]
    args.param = None if not args.param else "-" + args.param 

    return args


def usage_string(help_text, cmd):

    cmd_str = " ".join(cmd)
    for line in help_text:
        if cmd_str in line:
            return ">-" + line.strip()
    return None


# --- Main loop ------------------------------------------------------------- #
def main():

    args = parse_args()

    help_text = HelpText(args.command, help_param=args.param)
    help_text.read()
    inputs = help_text.parse()
    outputs = []
    usage_str = usage_string(help_text.text, args.command)

    tool_id = '_'.join(args.command).replace(":", "_")
    tool_object = CommandLineTool(
        tool_id=tool_id,
        base_command=args.command,
        doc=usage_str,
        cwl_version="v1.0",
    )
    tool_object.inputs = inputs
    tool_object.outputs = outputs

    if not inputs:
        print("Warning: No inputs found for '{}' '{}'".format(args.command, args.param))

    tool_object.export(args.output)
    print("Wrote tool to '{}'".format(args.output))


if __name__ == "__main__":
    main()
