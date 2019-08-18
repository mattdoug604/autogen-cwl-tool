import logging

from cwlgen import CommandInputParameter, CommandLineBinding, CommandLineTool


def arg_to_cwlgen(arg, position=0, **kwargs):

    cwl_binding = CommandLineBinding(prefix=arg.prefix, position=position)
    cwl_input = CommandInputParameter(
        arg.id,
        doc=arg.doc,
        input_binding=cwl_binding,
        param_type=arg.intype,
        **kwargs,
    )
    return cwl_input
