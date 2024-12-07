#!/usr/bin/env python3
"""
Provision plotting

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

from eval_results.scripts.plot.plotter import (INPUT_DIR, remove_head,
                                               mean_confidence_interval)
from src.lib import config


input_file = INPUT_DIR + "paillier/paillier.csv"
with open(input_file, "r", encoding='utf-8') as fd:
    lines = fd.readlines()
lines = remove_head(lines)

for i in range(7):
    j = i * 32
    data = [float(line.split(';')[1]) for line in lines[1+j : 31+j]]
    print(mean_confidence_interval(data))
