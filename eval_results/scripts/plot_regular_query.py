#!/usr/bin/env python3
"""
Regular query plotting

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import os

from eval_results.scripts.plot.colors import (maroon, red, yellow, pink, blue, green, orange)
from eval_results.scripts.plot.plotter import (EXTENSION, INPUT_DIR, OUTPUT_DIR, Line2D,
                                               Legend, plot_settings, read_data,
                                               convert_to_mb, convert_to_min,
                                               stacked_bar_plot_line, mean_confidence_interval)


X_INDEX = 2
SYNTHETIC = True
REAL = True

input_dir = INPUT_DIR + "regular_query/"
output_dir = OUTPUT_DIR + "regular_query/"
os.makedirs(output_dir, exist_ok=True)

diff = True
phases = ["Key Retrieval", "Point Retrieval", "Decryption"]
line_phases = ["To Key Server", "From Key Server",
               "To Map Server", "From Map Server"]

if SYNTHETIC:
    colors = [maroon, green, pink]
    line_colors = [yellow, orange, red, blue]
    r_indices = [3, 4, 5, 6]
    line_indices = [9, 7, 13, 11]
if REAL:
    time_indices = [3, 4, 5, 6]
    data_indices = [9, 7, 13, 11]


def subtract_prev(stack_lst: list[dict]) -> list[dict]:
    """Subtract the previous time."""
    for i in range(len(stack_lst) - 1, 0, -1):
        data = stack_lst[i]
        for p in data.keys():
            for j, t in enumerate(data[p]):
                data[p][j] = t - stack_lst[i-1][p][j]
    return stack_lst


def get_stacks(input_file: str, indices: list[int]) -> list[dict]:
    """Get stacks."""
    stacks = []
    for i in indices:
        d = read_data(input_file, X_INDEX, i)
        stacks.append(d)
    if diff:
        stacks = subtract_prev(stacks)
        del stacks[0]
    return stacks


if SYNTHETIC:
    r_1_stacks = get_stacks(input_dir + "regular_1_r_invalid.csv", r_indices)
    data_list = [[convert_to_min(stack) for stack in r_1_stacks]]

    diff = False
    line_1_stacks = get_stacks(input_dir + "regular_1_r_invalid.csv", line_indices)
    line_stacks_tks = dict([(0, line_1_stacks[0][2000]),
                            (1, line_1_stacks[0][4000]),
                            (2, line_1_stacks[0][6000])])
    line_stacks_fks = dict([(0, line_1_stacks[1][2000]),
                            (1, line_1_stacks[1][4000]),
                            (2, line_1_stacks[1][6000])])
    line_stacks_tms = dict([(0, line_1_stacks[2][2000]),
                            (1, line_1_stacks[2][4000]),
                            (2, line_1_stacks[2][6000])])
    line_stacks_fms = dict([(0, line_1_stacks[3][2000]),
                            (1, line_1_stacks[3][4000]),
                            (2, line_1_stacks[3][6000])])
    line_list = [line_stacks_tks, line_stacks_fks, line_stacks_tms, line_stacks_fms]
    line_list = [convert_to_mb(stack) for stack in line_list]

    tks_label = (Line2D([0], [0], color=line_colors[0], lw=1), "To Key Server")
    fks_label = (Line2D([0], [0], color=line_colors[1], lw=1), "From Key Server")
    tms_label = (Line2D([0], [0], color=line_colors[2], lw=1), "To Map Server")
    fms_label = (Line2D([0], [0], color=line_colors[3], lw=1), "From Map Server")
    line_labels = [tks_label, fks_label, tms_label, fms_label]

    with plot_settings(half_width=True):
        stacked_bar_plot_line(filename=output_dir + f"regular{EXTENSION}",
                            data_list=data_list,
                            line_list=line_list,
                            xlabel=r"Data Points [#]",
                            xlabels=[2000, 4000, 6000],
                            ylabel="Time [min]",
                            title="Execution Time and Transmitted Data "
                                "for Regular Query of 6000 Points",
                            stack_legend=Legend(phases, location='upper left', ncols=2,
                                                custom_labels=line_labels,
                                                empty_positions=[3]),
                            label_step=1,
                            colors=colors,
                            line_colors=line_colors,
                            second_y_axis=True,
                            second_y_label="Data [MB]",
                            second_ylim=15,
                            second_y_lim_bottom=0)

if REAL:
    r_1_stacks = get_stacks(input_dir + "regular_1_r_invalid_real.csv", time_indices)
    times = []
    for i in range(3):
        time = mean_confidence_interval(r_1_stacks[i][30])
        times.append(time)
        print(phases[i])
        print(time)
    print("Total Mean")
    print(sum(times[i][0] for i in range(3)))
    print("Total Deviation")
    print(sum(times[i][1] for i in range(3)))
    print("\n")

    diff = False

    data_1_stacks = get_stacks(input_dir + "regular_1_r_invalid_real.csv", data_indices)
    data_1_stacks = [convert_to_mb(stack) for stack in data_1_stacks]
    datas = []
    for i in range(4):
        data = mean_confidence_interval(data_1_stacks[i][30])
        datas.append(data)
        print(line_phases[i])
        print(data)
    print("Total Mean")
    print(sum(datas[i][0] for i in range(4)))
    print("Total Deviation")
    print(sum(datas[i][1] for i in range(4)))
