#!/usr/bin/env python3
"""
Reverse query plotting

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import os

from eval_results.scripts.plot.colors import (maroon, red, yellow, purple, pink, blue, green,orange)
from eval_results.scripts.plot.plotter import (INPUT_DIR, OUTPUT_DIR, EXTENSION, Line2D,
                                               Legend, plot_settings, read_data,
                                               convert_to_mb, convert_to_min, stacked_bar_plot_line)


X_INDEX = 2
SYNTHETIC = True

input_dir = INPUT_DIR + "reverse_query/"
output_dir = OUTPUT_DIR + "reverse_query/"
os.makedirs(output_dir, exist_ok=True)

if SYNTHETIC:
    diff = True
    phases = ["Key Retrieval", "Point Retrieval",
              "Obfuscation", "Decryption"]
    colors = [maroon, green, purple, pink]
    line_colors = [yellow, orange, red, blue]
    r_indices = [5, 6, 7, 8]
    line_indices = [11, 9, 15, 13]


def subtract_prev(stack_lst: list[dict]) -> list[dict]:
    """Subtract the previous time."""
    for i in range(len(stack_lst) - 1, 0, -1):
        data = stack_lst[i]
        for p in data.keys():
            for j, t in enumerate(data[p]):
                data[p][j] = t - stack_lst[i-1][p][j]
    return stack_lst


def get_stacks_tc(file: str, x_index: int, y_index: int = -1) -> dict:
    """Get stacks without traffic control."""
    with open(file, "r", encoding='utf-8') as fd:
        lines = fd.readlines()
    found = False
    i = 0
    while not found:
        if "END HEADER" in lines[i]:
            found = True
        else:
            i += 1
    lines = lines[i + 1:]

    result = {}
    for line in lines:
        values = line.split(";")
        if int(values[3]) or int(values[4]):
            continue
        x = int(values[x_index])
        y = float(values[y_index])
        if x in result:
            result[x].append(y)
        else:
            result[x] = [y]
    return result


def get_stacks(input_file: str, indices: list[int], tc: bool = False) -> list[dict]:
    """Get stacks."""
    stacks = []
    for i in indices:
        d = read_data(input_file, X_INDEX, i)
        if tc:
            d = get_stacks_tc(input_file, X_INDEX, i)
        stacks.append(d)
    if diff:
        stacks = subtract_prev(stacks)
        del stacks[0]
    return stacks


if SYNTHETIC:
    r_stacks = get_stacks(input_dir + "reverse_r_invalid.csv", r_indices, True)
    regular_stacks = get_stacks(INPUT_DIR + "regular_query/regular_1_r_invalid.csv", [4, 5])
    for i in range(1, 4):
        for j in range(30):
            k = i * 2000
            r_stacks[1][i][j] -= regular_stacks[0][k][j]
    r_stacks.insert(1, dict([(1, regular_stacks[0][2000]),
                             (2, regular_stacks[0][4000]),
                             (3, regular_stacks[0][6000])]))
    data_list = [[convert_to_min(stack) for stack in r_stacks]]

    diff = False
    line_1_stacks = get_stacks(input_dir + "reverse_r_invalid.csv", line_indices)
    line_stacks_tks = dict([(0, line_1_stacks[0][1]),
                            (1, line_1_stacks[0][2]),
                            (2, line_1_stacks[0][3])])
    line_stacks_fks = dict([(0, line_1_stacks[1][1]),
                            (1, line_1_stacks[1][2]),
                            (2, line_1_stacks[1][3])])
    line_stacks_tms = dict([(0, line_1_stacks[2][1]),
                            (1, line_1_stacks[2][2]),
                            (2, line_1_stacks[2][3])])
    line_stacks_fms = dict([(0, line_1_stacks[3][1]),
                            (1, line_1_stacks[3][2]),
                            (2, line_1_stacks[3][3])])
    line_list = [line_stacks_tks, line_stacks_fks, line_stacks_tms, line_stacks_fms]
    line_list = [convert_to_mb(stack) for stack in line_list]

    tks_label = (Line2D([0], [0], color=line_colors[0], lw=1), "To Key Server")
    fks_label = (Line2D([0], [0], color=line_colors[1], lw=1), "From Key Server")
    tms_label = (Line2D([0], [0], color=line_colors[2], lw=1), "To Map Server")
    fms_label = (Line2D([0], [0], color=line_colors[3], lw=1), "From Map Server")
    line_labels = [tks_label, fks_label, tms_label, fms_label]

    with plot_settings(half_width=True):
        stacked_bar_plot_line(filename=output_dir + f"reverse{EXTENSION}",
                            data_list=data_list,
                            line_list=line_list,
                            xlabel="Map Previews [#]",
                            xlabels=[1, 2, 3],
                            ylabel="Time [min]",
                            title="Execution Time and Transmitted Data "
                                "for Reverse Query",
                            stack_legend=Legend(phases, location='upper left', ncols=2,
                                                custom_labels=line_labels),
                            label_step=1,
                            colors=colors,
                            line_colors=line_colors,
                            second_y_axis=True,
                            second_y_label="Data [MB]",
                            second_ylim=15,
                            second_y_lim_bottom=0)
