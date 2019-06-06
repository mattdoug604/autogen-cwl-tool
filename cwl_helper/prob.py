#!/usr/bin/env python

import re
import sys
from collections import defaultdict, namedtuple

import numpy as np
import pandas as pd

from constants import __program__, __version__, TYPE_LIST, RE_PREFIX, RE_TYPE, RE_LIST


def detect_outlier(data, point, threshold=0.5):
    
    mean = np.median(data)
    std = np.std(data)
    
    z_score = (point - mean) / std
    return np.abs(z_score) > threshold


def iter_text(text):

    prfx_list = []
    type_list = []
    prfx_ranges = defaultdict(list)
    type_ranges = defaultdict(list)

    # munge each line in the help text
    for line in text:

        # match argument prefix(es)
        for match in re.finditer(RE_PREFIX, line):
            start = match.span()[0]
            match = match.group(0).strip()
            prfx_list.append(start)
            prfx_ranges[start].append((match, line.lstrip()))
        # match recognized input type
        for match in re.finditer(RE_TYPE, line, flags=re.IGNORECASE):
            start = match.span()[0]
            match = match.group(0).strip()
            type_list.append(start)
            type_ranges[start].append((match, line.lstrip()))

    print('Prefixes:')
    for start in sorted(prfx_ranges):
        print(start)
        for match, line in prfx_ranges[start]:
            print('\t{}\t\t=> {}'.format(match, line))
    print('Type:')
    for start in sorted(type_ranges):
        print(start)
        for match, line in type_ranges[start]:
            print('\t{}\t\t=> {}'.format(match, line))

    print('Prefixes:')
    y = sum([len(val) for val in prfx_ranges.values()])
    for n in sorted(set(prfx_ranges)):
        x = len(prfx_ranges[n])
        z = x / y
        print('{} = {}, {}'.format(n, z, detect_outlier(prfx_list, n)))
    print('Type:')
    y = sum([len(val) for val in type_ranges.values()])
    for n in sorted(set(type_ranges)):
        x = len(type_ranges[n])
        z = x / y
        print('{} = {}, {}'.format(n, z, detect_outlier(type_list, n)))


if __name__ == '__main__':

    with open(sys.argv[1], 'r') as fh:
        text = fh.readlines()

    iter_text(text)