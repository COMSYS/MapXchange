"""
Plotting functions for eval results

Copyright (c) 2024.
Author: Joseph Leisten
E-mail: joseph.leisten@rwth-aachen.de
"""

import json
import math
import os
from contextlib import contextmanager

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats
from matplotlib import patches, transforms
from matplotlib import ticker
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.constants import golden as golden_ratio

from eval_results.scripts.plot.colors import bar_colors, blue, orange
from src.lib import config


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
EXTENSION = '.pdf'
PRINT = True
TITLE = False


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Default Settings
# -----------------------------------------------------------------------------
def cm(value: float | int) -> float:
    """Calculate the number that has to be given as size to obtain cm."""
    return value / 2.54


def golden_height(width: float) -> float:
    """Return the height corresponding to the golden ratio of a given width."""
    return (1.0 / golden_ratio) * width


INPUT_DIR = config.EVAL_DIR
OUTPUT_DIR = os.path.dirname(config.WORKING_DIR) + '/eval_results/plots/'
os.makedirs(OUTPUT_DIR, exist_ok=True)
y_lim_fac = 1.25
figure_width = 427.43153 * 0.03514
figure_height = 5.0
font_size = 9
ticks_fontsize = font_size - 1
legend_font_size = font_size - 1
default_settings = {
    # By Roman
    'figure.figsize': (cm(figure_width), cm(figure_height)),
    'font.size': font_size,
    'legend.fontsize': legend_font_size,
    'axes.titlesize': font_size,
    'axes.labelsize': font_size,
    'ytick.labelsize': ticks_fontsize,
    'xtick.labelsize': ticks_fontsize,
    'hatch.linewidth': 0.8,
    'xtick.minor.pad': 1,
    'axes.labelpad': 3,
    # By Erik
    'legend.framealpha': 1,
    'legend.edgecolor': 'black',
    'legend.fancybox': False,
    'legend.handletextpad': 0.2,
    'legend.columnspacing': 0.8,
    'figure.dpi': 1000,
    'legend.facecolor': 'white',
    'lines.linewidth': 1.5,
    'errorbar.capsize': 3,
    'lines.markeredgewidth': 0.7,
    'lines.markersize': 3,
}
plt.rcParams.update(default_settings)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Helper functins
# -----------------------------------------------------------------------------

class Legend(object):
    """Represents a legend object

    empty_positions: Empty spaces in legend
    order: Reorder legend according to list
    axis: The axis to add the legend to
    markers: List of plot objects
    legend_labels: The labels to use
    location: 'top' or default matplotlib values
    """
    STACKS: str = 'STACKS'
    BARS: str = 'BARS'
    TOP: str = 'top'
    target: str = STACKS
    location: str = None
    markers: list = []
    ncols: int = None
    labels: list[str] = []
    axis = plt
    order: tuple[int] | list[int] = None
    empty_positions: list[int] = None
    custom_labels: list[tuple] = None

    def __init__(self, labels: list[str], location: str = None,
                 custom_labels: list[tuple] = None,
                 empty_positions: list[int] = None,
                 order: tuple[int] | list[int] = None,
                 ncols: int = None):
        self.labels = labels
        self.location = location
        self.custom_labels = custom_labels
        self.empty_positions = empty_positions
        self.order = order
        self.ncols = ncols

    def make(self):
        """Add legend to axis"""
        if self.empty_positions is not None:
            r = patches.Rectangle((0, 0), 1, 1, fill=False,
                                  edgecolor='none',
                                  visible=False)
            for pos in self.empty_positions:
                self.labels.insert(pos, "")
                self.markers.insert(pos, r)
        if self.custom_labels is not None:
            if len(self.labels) == 0:
                # Only custom labels wanted
                self.markers = []
            for m, t in self.custom_labels:
                self.markers.append(m)
                self.labels.append(t)
        if self.order is not None:
            self.markers = [self.markers[i] for i in self.order]
            self.labels = [self.labels[i] for i in self.order]
        if self.ncols is not None:
            columns = self.ncols
        elif len(self.labels) <= 5:
            columns = len(self.labels)
        else:
            columns = math.ceil(len(self.labels) / 2)
        if self.location == "top":
            legend = self.axis.legend(self.markers, self.labels,
                                      loc='center', ncol=columns,
                                      bbox_to_anchor=(0.5, 1))
        elif self.location == 'above':
            legend = self.axis.legend(self.markers, self.labels,
                                      loc='lower center', ncol=columns,
                                      bbox_to_anchor=(0.5, 1))
        else:
            # Best location
            legend = self.axis.legend(self.markers, self.labels,
                                      loc=self.location, ncol=columns)
        legend.get_frame().set_linewidth(0.4)
        return legend


def set_minor_xticks(ax: Axes, minor_xticks: list[float],
                     minor_xlabels: list[str],
                     rotation: float = None,
                     labelsize: float = None):
    """Set minor xticks"""
    if minor_xticks is not None:
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor_xticks))
        ax.xaxis.set_minor_formatter(ticker.FixedFormatter(minor_xlabels))
        if labelsize is not None:
            ax.xaxis.set_tick_params(which='minor', labelsize=labelsize)
        if rotation is not None:
            ax.xaxis.set_tick_params(which='minor', rotation=rotation)


@contextmanager
def plot_settings(params: dict = None,
                  half_width: bool = False,
                  two_third: bool = False):
    """Update the rcParams for one plot only"""
    if params is None:
        params = {}
    if half_width:
        params = {
            'font.size': font_size - 2.4,
            'legend.fontsize': legend_font_size - 4.4,
            'axes.titlesize': font_size - 2.4,
            'axes.labelsize': font_size - 2.4,
            'ytick.labelsize': ticks_fontsize - 2.4,
            'xtick.labelsize': ticks_fontsize - 2.4,
            'figure.figsize': (
                cm(figure_width) / 2, cm(5.0) * 2 / 3)
        }
    if two_third:
        params['figure.figsize'] = (
            cm(figure_width), cm(figure_height) * 2 / 3)
    plt.rcParams.update(params)
    yield
    plt.rcParams.update(default_settings)


# noinspection PyUnresolvedReferences
def crop_plot(adjust: list | tuple,
              figure: Figure,
              hspace: float = None,
              divider: bool = False
              ) -> None:
    """Adjust plot margin"""
    if adjust is not None:
        figure.subplots_adjust(left=adjust[0], right=adjust[1], top=adjust[2],
                               bottom=adjust[3])
    else:
        figure.tight_layout()
        if divider:
            # We need more space because of axis dividers
            right_offset = 0
            left_offset = 0.012
            bottom_offset = 0.05
            top_offset = 0.04
        else:
            right_offset = 0.01
            left_offset = 0.02
            bottom_offset = 0.05
            top_offset = 0.04
        figure.subplots_adjust(
            left=figure.subplotpars.left - left_offset,
            right=figure.subplotpars.right + right_offset,
            top=figure.subplotpars.top + top_offset,
            bottom=figure.subplotpars.bottom - bottom_offset,
        )
    plt.subplots_adjust(hspace=hspace)


def output(filename: str) -> None:
    """Print to file or show."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    if PRINT:
        print(f"Print to: {filename}")
        plt.savefig(filename)
    else:
        plt.show()
    plt.close()


def add_gray_bars(axis: Axes, gray_bg: list[tuple]):
    """Add vertical gray BG"""
    res = []
    if gray_bg is not None:
        for start, end, color in gray_bg:
            res.append(
                axis.axvspan(start, end, facecolor=color, alpha=0.5,
                             zorder=-1))
    return res


def add_text_boxes_into_bars(axis: Axes, text_boxes: list[dict],
                             bars: list[patches.Polygon]):
    """Add Text Boxes into the gray bars"""
    for t in text_boxes:
        lower_left = bars[t['i']].xy[0]
        upper_right = bars[t['i']].xy[2]
        del t['i']
        x = (lower_left[0] + upper_right[0]) / 2
        y = t['y']
        del t['y']
        trans = transforms.blended_transform_factory(
            axis.transData, axis.transAxes)
        axis.text(x, y, **t, transform=trans,
                  horizontalalignment='center',
                  verticalalignment='center')


def mean_confidence_interval(data: list, confidence: float = 0.99) -> \
        tuple[float, float]:
    """
    Compute mean and corresponding confidence interval of given data.

    :param data: List of numbers to compute mean and interval for
    :param confidence: Confidence interval to use, default: 99%
    """
    a = 1.0 * np.array(data)
    n = len(a)
    if n == 1:
        return a[0], 0
    m, se = np.mean(a), scipy.stats.sem(a)
    h: float = se * scipy.stats.t.ppf((1 + confidence) / 2., n - 1)
    return float(m), h


def convert_to_mb(data: dict) -> dict:
    """Divide all keys by 10^6"""
    for x in data:
        data[x] = [y / 1000000 for y in data[x]]
    return data

def convert_to_min(data: dict) -> dict:
    """Divide all y-values by 60."""
    for x in data:
        data[x] = [y / 60 for y in data[x]]
    return data


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Read input from file
# -----------------------------------------------------------------------------
def remove_head(lines: list[str]) -> list[str]:
    """Remove header from list of lines."""
    i = 0
    while True:
        if "END HEADER" in lines[i]:
            break
        else:
            i += 1
    return lines[i + 1:]


def read_data(file: str, x_index: int, y_index: int = -1) -> dict:
    """
    Read the data from a file.
    :param file: Input file
    :param x_index: Index of X column
    :param y_index: [optional] Index of Y column
    :return: Dict in following Format:
    X-values as keys, Y-values as List, even if there is only one.
    {
        x1: [y1, y2, y3],
        x2: [y4],
        x3. [y5, y6]
    }
    """
    with open(file, "r", encoding='utf-8') as fd:
        lines = fd.readlines()
    lines = remove_head(lines)

    # Read out data
    result = {}
    for line in lines:
        values = line.split(";")
        x = int(values[x_index])
        y = float(values[y_index])
        if x in result:
            result[x].append(y)
        else:
            result[x] = [y]
    return result


def read_data_mult(file: str, x_index: int, y_index_start: int, y_index_end: int,
                   z_index: int, z_zero: int) -> dict[int, dict]:
    """
    Read multiple data dicts from a file.

    :param file: Input file
    :param x_index: Index of X column
    :param y_index: [optional] Index of Y column
    :param z_index: The index of the different curves
    :param z_zero: Index of values that have to be zero
    :return: Dict of dicts in following Format:
    X-values as keys, Y-values as List, even if there is only one.
    {
        z1:{
            x1: [y1, y2, y3],
            x2: [y4],
            x3. [y5, y6]
        },
        z2:{
            x1: [y1, y2, y3],
            x2: [y4],
            x3. [y5, y6]
        }
    }
    """
    with open(file, "r", encoding='utf-8') as fd:
        lines = fd.readlines()
    lines = remove_head(lines)

    # Read out data
    result = {}
    for line in lines:
        values = line.split(";")
        if int(values[z_zero]):
            continue
        x = int(values[x_index])
        y = float(values[y_index_end]) - float(values[y_index_start])
        z = int(values[z_index])
        if z not in result:
            result[z] = {}
        if x in result[z]:
            result[z][x].append(y)
        else:
            result[z][x] = [y]
    return result


def read_ram(file: str, x_index: int, y_index: int = -1) -> dict:
    """
    Read maximal ram value for each x.
    :param file: Input file
    :param x_index: Index of X column
    :param y_index: [optional] Index of Y column
    :param x_is_float: [optional] x is interpreted as float instead of int
    :return: Dict in following Format:
    X-values as keys, Y-values as List, even if there is only one.
    {
        x1: [y1, y2, y3],
        x2: [y4],
        x3. [y5, y6]
    }
    """
    with open(file, "r", encoding='utf-8') as fd:
        lines = fd.readlines()
    lines = remove_head(lines)

    # Read out data
    result = {}
    for line in lines:
        values = line.split(";")
        x = int(values[x_index])
        ram_value = json.loads(values[y_index])
        y = float(ram_value[0])
        if x in result:
            result[x].append(y)
        else:
            result[x] = [y]
    return result


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Plot Scripts
# -----------------------------------------------------------------------------
def box_plot(
        data,
        filename,
        x_step,
        min_y,
        max_y,
        y_step,
        xlabel,
        ylabel,
        title,
        adjust,
        x_label_step=1) -> None:
    """
    Create a box plot with errorbars
    :param data: Data in the following Format:
        A dict with the X-Values as keys and the Y-Values as a list (even
        if there is only one Y-Value per X-value).
        { x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
    :param filename: Output filename
    :param x_step: Stepsize of xticks
    :param min_y: Start of Y-Axis
    :param max_y: Maximal ytick
    :param y_step: Stepsize of yticks
    :param xlabel: Large Label of X-Axis
    :param ylabel: Large Label of Y-Axis
    :param title: Title of Plot
    :param adjust: Tuple with 4 values (left, right, top, bottom)
    :param x_label_step: [optional] Evey ith label printed on x-axis
    :return: None
    """
    fig, ax = plt.subplots()

    # Construct value list
    x_values = sorted(data.keys())
    y_values = []
    for x in x_values:
        y_values.append(data[x])

    # Calculate positions of boxes
    n = len(y_values)
    xticks = np.arange(x_step, n * x_step + 1, x_step)

    # Plot
    boxplot = ax.boxplot(
        y_values,
        False,
        None,  # No outliers
        True,
        1.5,
        widths=x_step / 1.25,  # Width of boxes
        showmeans=True,  # Show average
        positions=xticks  # Position of boxes
    )

    # Set colors
    plt.setp(boxplot['whiskers'], color='blue')
    plt.setp(boxplot['medians'], color='red')
    plt.setp(boxplot['means'], color='red')
    plt.setp(boxplot['boxes'], color='blue')

    # Set axis labels
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    # Set Title
    if TITLE:
        plt.title(title, y=0.98)

    # Set size of axis and caption
    plt.xlim([0, (n + 1) * x_step])

    # Only label every ith x-tick
    for i in range(0, len(x_values), 1):
        if i % x_label_step != 0:
            x_values[i] = ''
    # X-Ticks
    plt.xticks(xticks, x_values)

    # Y-Ticks
    plt.yticks(np.arange(min_y, max_y + y_step, y_step))

    # Crop
    crop_plot(adjust, figure=fig)

    output(filename)


def convert_numbers_to_str(xlabels: list[float] | list[int] | list[str]):
    """
    Format the labels in textual form like Mil/Bil etc.
    :param xlabels: The xlabels to edit
    :return: Edited xlabels
    """
    for i, t in enumerate(xlabels):
        if t < 1000:
            xlabels[i] = f"{t}"
        elif t < 1000000:
            xlabels[i] = f"{(t // 1000):1} k"
        elif t < 1000000000:
            xlabels[i] = f"{t // 1000000} Mio"
        elif t < 1000000000000:
            xlabels[i] = f"{t // 1000000000} Bil"
        else:
            xlabels[i] = f"{t:.{1}E}"
    return xlabels


def set_xticks(axis: Axes, xticks: list[float], xlabels: list[str],
               minor_xticks: list[float], minor_xlabels: list[str],
               x_values: list[float], x_step: float,
               x_label_step: int,
               logarithmic: bool,
               center_xlabels: bool,
               x_rotation: float,
               log_base: int = 1):
    """
    Add formatted xticks to axis
    :param axis: Axis to add labels to
    :param xticks: Locations of major xticks
    :param xlabels: Labels of major xticks
    :param minor_xticks: Locations of minor xticks
    :param minor_xlabels: Labels of minor xticks
    :param x_values: X-Values used by Plot
    :param x_step: Step value for xticks
    :param x_label_step: Only label every ith with major + label
    :param logarithmic: logarithmic axis?
    :param center_xlabels: Put labels between texts
    :param x_rotation: Rotate labels
    :param log_base: [optional] Log Base
    """
    if logarithmic:
        min_tick = math.log(min(x_values), log_base)
        max_tick = math.log(max(x_values), log_base)
        if min_tick > 0:
            min_tick = int(math.ceil(min_tick))
            max_tick = int(math.ceil(max_tick))
        else:
            min_tick = int(math.floor(min_tick))
            max_tick = int(math.floor(max_tick))
    else:
        min_tick, max_tick = None, None

    # Define xticks
    if xticks is None:
        if logarithmic:
            xticks = [log_base ** i for i in range(min_tick, max_tick + 1)]
        else:
            xticks = list(np.arange(0, max(x_values) + 1, x_step))

    # Define xlabels
    if xlabels is None:
        if logarithmic:
            # Logarithmic Axis
            xlabels = [
                fr"{log_base}^{{{i}}}"
                for i in range(min_tick, max_tick + 1)
            ]
        else:
            # Normal Scale
            xlabels = list(xticks[:])
            xlabels = convert_numbers_to_str(xlabels)

    if minor_xticks is None:
        minor_xticks = []
    if minor_xlabels is None:
        minor_xlabels = []

    # Make unlabeled ticks minor
    remove_indices = []
    for i in range(0, len(xticks[:]), 1):
        if i % x_label_step != 0:
            # noinspection PyTypeChecker
            minor_xticks.append(xticks[i])
            minor_xlabels.append('')
            remove_indices.append(i)
    for i in sorted(remove_indices, reverse=True):
        del xticks[i]
        del xlabels[i]

    # Label
    if center_xlabels:
        axis.set_xlim(0, max(x_values))
        axis.xaxis.set_major_locator(ticker.FixedLocator(xticks))

        # Com Text pos
        ticks = [0] + list(xticks)
        minor_ticks = []
        for i, t in enumerate(ticks[1:]):
            minor_ticks.append((t + ticks[i]) / 2)
        axis.xaxis.set_minor_locator(ticker.FixedLocator(minor_ticks))

        axis.xaxis.set_major_formatter(ticker.NullFormatter())
        axis.xaxis.set_minor_formatter(ticker.FixedFormatter(xlabels))

        for tick in axis.xaxis.get_minor_ticks():
            tick.label.set_fontsize(ticks_fontsize)
            tick.tick1line.set_markersize(0)
            tick.tick2line.set_markersize(0)
            tick.label1.set_horizontalalignment('center')
    else:
        axis.set_xticks(xticks)
        axis.set_xticklabels(xlabels)
        if x_rotation is not None:
            axis.xaxis.set_tick_params(which='major',
                                       labelrotation=x_rotation)
            # fontdict={
            #     'horizontalalignment': 'right',
            #     'labelrotation': x_rotation})

    set_minor_xticks(axis, minor_xticks, minor_xlabels, x_rotation)


def set_yticks(axis: Axes, yticks: list[float], ylabels: list[str],
               min_y: float, max_y: float, y_step: float,
               logarithmic: bool, y_label_step: int, scientific_y: bool,
               log_base: int = 10):
    """
    Add Y-Ticks to axis
    :param axis: Axis to add ticks to
    :param yticks: Major Y-Tick Locations
    :param ylabels: Major Y-Tick Labels
    :param min_y: Minimal Y Value
    :param max_y: Maximal Y Value
    :param y_step: Y Step
    :param logarithmic: Axis logarithmic?
    :param y_label_step: Only label every ith with major tick + label
    :param scientific_y: Scientific Format?
    :param log_base: [optional] Log Base
    """
    if ylabels is None:
        if not logarithmic:
            yticks = np.arange(min_y, max_y + y_step, y_step)
            if ylabels is None:
                if scientific_y:
                    ylabels = [f"{e:.{1}E}" for e in yticks]
                else:
                    ylabels = list(yticks[:])
                    ylabels = convert_numbers_to_str(ylabels)
        else:
            # Logarithmic scale
            max_tick = int(math.ceil(math.log(max_y, log_base)))
            yticks = [log_base ** i for i in range(max_tick + 1)]
            ylabels = yticks

    # Only label every ith y-tick
    for i in range(0, len(ylabels)):
        if i % y_label_step != 0:
            ylabels[i] = ''

    # Label
    plt.yticks(yticks, ylabels)


def error_plot_mult(
        filename: str,
        data_list: list[dict],
        x_step: float,
        min_y: float,
        max_y: float,
        y_step: float,
        xlabel: str,
        ylabel: str,
        title: str,
        legend: Legend = None,
        adjust: list | tuple = None,
        x_label_step: int = 1,
        y_label_step: int = 1,
        scientific_y: bool = False,
        x_log: bool = False,
        y_log: bool = False,
        xticks: list[float] = None,
        xlabels: list[str] = None,
        minor_xticks: list[float] = None,
        minor_xlabels: list[str] = None,
        yticks: list[float] = None,
        ylabels: list[str] = None,
        x_sync: bool = False,
        log_base=10,
        reverse_x: bool = True,
        grid: bool = False,
        ver_grid: bool = False,
        hor_grid: bool = False,
        fmts: list[str] = None,
        y_lim: int = None,
        y_lim_bottom: int = None,
        center_x_labels: bool = False,
        x_rotation: float = None,
        auto_ylabels: bool = False,
        second_y_axis: list[int] = None,
        second_y_label: str = None,
        colors: list[str] = bar_colors,
        second_ylim: float = None,
        second_y_lim_bottom: int = None,
) -> None:
    """
    Create multiple lineplots in one plot
    :param filename: Output filename
    :param data_list: List of Data Dicts in the following Format:
        A dict with the X-Values as keys and the Y-Values as a list (even
        if there is only one Y-Value per X-value).
        { x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
    :param x_step: Stepsize of xticks
    :param min_y: Start of Y-Axis
    :param max_y: Maximal ytick
    :param y_step: Stepsize of yticks
    :param xlabel: Large Label of X-Axis
    :param ylabel: Large Label of Y-Axis
    :param title: Title of Plot
    :param legend: [optional] Legend object
    :param adjust: [optional] Tuple with 4 values (left, right, top, bottom)
    :param x_label_step: [optional] Evey ith label printed on X-Axis
    :param y_label_step: [optional] Evey ith label printed on >-Axis
    :param scientific_y: [optional] Y-ticks in scientific representation
    :param x_log: [optional] Logarithmic X-Axis if True
    :param y_log: [optional] Logarithmic Y-Axis if True
    :param xticks: [optional] Location of X-Ticks
    :param xlabels: [optional] Text of X-Ticks
    :param minor_xticks: [optional] Location of minor X-Ticks
    :param minor_xlabels: [optional] Text of minor X-Ticks
    :param yticks: Location of Y-Ticks
    :param ylabels: [optional] Text of Y-Ticks
    :param x_sync: [optional] If True, don't set xlim to 0
    :param log_base: [optional] Base for logarithmic Axes
    :param reverse_x: [optional] Reverse X-Values
    :param grid: [optional] Display Grid behind plot
    :param fmts: [optional] Line styles
    :param hor_grid: [optional] Show horizontal Grid
    :param ver_grid: [optional] Show vertical Grid
    :param y_lim: [optional] Explicit upper limit on y
    :param y_lim_bottom: [optional] Explicit lower limit on y
    :param x_rotation: [optional] Rotation degree of xlabels
    :param auto_ylabels: [optional] Use auto ylabels
    :param second_ylim: [optional] Second axis' ylim
    :param second_y_lim_bottom: [optional] Explicit lower limit on second y
    :param colors: [optional] Colors of lines
    :param second_y_axis: [optional] List of 0 or 1 to assign each line to
    one axis
    :param second_y_label: [optional] Label for second Y axis
    :param center_x_labels: Should xlabels be centered between ticks?
    :return: None
    """
    fig, ax1 = plt.subplots()
    if second_y_axis is not None:
        ax2 = ax1.twinx()
    else:
        ax2 = None

    # Construct value lists
    x_values = sorted(data_list[0].keys(), reverse=reverse_x)
    y_values = []
    for i, d in enumerate(data_list):
        y_values.append([])
        for x in x_values:
            y_values[i].append(d[x])

    # Compute means and errors.
    y_means = []
    y_errors = []
    for i, d in enumerate(data_list):
        y_means.append([])
        y_errors.append([])
        for y in y_values[i]:
            m, h = mean_confidence_interval(y, 0.95)
            y_means[i].append(m)
            y_errors[i].append(h)

    # Plot
    plts = []
    if len(data_list) <= 2:
        colors = [blue, orange]
    axes = [ax1, ax2]
    for i, d in enumerate(data_list):
        if second_y_axis is not None:
            ax = axes[second_y_axis[i]]
        else:
            ax = ax1
        plts.append(ax.errorbar(
            x_values,
            y_means[i],
            yerr=y_errors[i],
            fmt='-' if fmts is None else fmts[i],
            color=colors[i],
            ecolor='black',
            elinewidth=1,  # Dicke des vertikalen Strichs
            barsabove=True,
        ))

    # Set axis labels
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    if second_y_label:
        ax2.set_ylabel(second_y_label)

    # Set Title
    if TITLE:
        plt.title(title, y=0.98)

    # Set size of axis and caption
    if not x_sync:
        ax1.set_xlim([0, max(x_values)])
    else:
        ax1.set_xlim(sorted([min(x_values), max(x_values)], reverse=reverse_x))

    # Define bottom
    if y_lim_bottom is not None:
        ax1.set_ylim(bottom=y_lim_bottom)
    elif y_log:
        # Automatic
        pass
    else:
        ax1.set_ylim(bottom=0)
    if second_ylim:
        ax2.set_ylim(top=second_ylim)
    if second_y_lim_bottom is not None:
        ax2.set_ylim(bottom=second_y_lim_bottom)

    # Custom upper limit
    if y_lim is not None:
        ax1.set_ylim(top=y_lim)

    # Type of Axis ------------------------------------------------------------
    # Logarithmic X Axis:
    if x_log:
        ax1.set_xscale('log')

    # Logarithmic Y Axis:
    if y_log:
        ax1.set_yscale('log')

    # X-Axis Labels -----------------------------------------------------------
    set_xticks(ax1, xticks, xlabels, minor_xticks, minor_xlabels, x_values,
               x_step, x_label_step, x_log, center_x_labels, x_rotation,
               log_base)

    # -------------------------------------------------------------------------
    # Y-Axis labels -----------------------------------------------------------
    if not auto_ylabels:
        set_yticks(ax1, yticks, ylabels, min_y, max_y, y_step, y_log,
                   y_label_step, scientific_y, log_base)
    # -------------------------------------------------------------------------

    if grid:
        ver_grid = True
        hor_grid = True
    ax1.yaxis.grid(hor_grid)
    ax1.xaxis.grid(ver_grid)

    # Legend
    if len(data_list) > 1:
        legend.markers = [p[0] for p in plts]
        legend.make()

    # Crop
    crop_plot(adjust, figure=fig)

    output(filename)


class BarText(object):
    """
    Represents a text that can be added to a bar.
    """

    fontsize: float = font_size
    rotation: float = 90
    color: str = "black"

    def __init__(self,
                 bar_id: int,
                 stack_id: int,
                 x_value: float,
                 axis_id: int,
                 text: str,
                 loc: str,
                 rotation: float = 90,
                 color: str = 'black'
                 ):
        """
        Initialize object with values
        :param bar_id: The bar to add text to
        :param stack_id: The stack to add text to
        :param x_value: The x_value to add text to. (Max be +0.5 for in
        between)
        :param axis_id: The axis to add to
        :param text: The text
        :param loc: 'in' for within bar, 'on' for on top of bar,
                    'center' for centered in Y-Axis
        """
        self.bar_id = bar_id
        self.stack_id = stack_id
        self.x_value = x_value
        self.axis_id = axis_id
        self.text = text
        self.loc = loc
        self.rotation = rotation
        self.color = color


def add_bar_text(bar_texts: list[BarText], bar_id: int, stack_id: int,
                 bar_lists: list[BarContainer], axes: list[Axes]):
    """Add text to bars."""
    for bt in bar_texts:
        a, b, x, t, loc, ax_id = bt.bar_id, bt.stack_id, bt.x_value, \
                                 bt.text, bt.loc, bt.axis_id
        ax = axes[ax_id]
        bar_list = bar_lists[ax_id]
        if bar_id == a and stack_id == b:
            for idx, rect in enumerate(bar_list):
                if x == 'all' or x == idx or x == idx + 0.5:
                    # Wenn der Matching Balken groß genug ist,
                    # kann es auf den Balken geschrieben werden
                    # Wenn nicht, und die Balken sehr klein sind
                    # Centered man den Text vertikal
                    # und wenn das auch nicht geht, dann einfach
                    # über die Bar
                    x_value = rect.get_x()
                    height = rect.get_height()
                    ha = 'center'
                    if x == idx + 0.5:
                        # In between bars
                        # noinspection PyUnresolvedReferences
                        x_value = (rect.get_x() + bar_list[
                            idx + 1].get_x() + rect.get_width()) / 2.
                    else:
                        x_value += rect.get_width() / 2.
                    trans, va = ax.transData, 'center'
                    if loc == 'in':
                        y = rect.get_y() + 0.5 * height
                    elif loc == 'on':
                        y = rect.get_y() + 1.1 * height
                        va = 'bottom'
                    elif loc == 'center':
                        # center
                        y = 0.5
                        trans = \
                            transforms.blended_transform_factory(
                                ax.transData, ax.transAxes)
                    elif loc == 'between':
                        y = 1
                        trans = \
                            transforms.blended_transform_factory(
                                ax.transData, ax.transAxes)
                    else:
                        raise RuntimeError("Unknown location")
                    ax.text(
                        x_value,
                        y, t, transform=trans,
                        ha=ha, va=va,
                        rotation=bt.rotation,
                        fontsize=bt.fontsize,
                        color=bt.color
                    )


def stacked_bar_plot_mult(
        filename: str,
        data_list: list[list[dict]],
        xlabel: str,
        ylabel: str,
        title: str,
        bar_legend: Legend = None,
        stack_legend: Legend = None,
        adjust: list | tuple = None,
        y_log: bool = False,
        x_log: bool = False,
        xticks: list[int] = None,
        xlabels: list[str] = None,
        minor_xticks: list[int] = None,
        minor_xlabels: list[str] = None,
        stacks_depend_on_prev=False,
        label_step: int = 1,
        colors: list[str] = bar_colors,
        hatches: list[str] = None,
        y_lim: float = None,
        backgrounds: list[tuple] = None,
        text_boxes: list[dict] = tuple(),
        order: list[int] = None,
        rotate_xticks: bool = False,
        colors_depend_on_bar: bool = False,
        divide_y: bool = False,
        ymin: float = None,
        ymax: float = None,
        ymin2: float = None,
        ymax2: float = None,
        y_label_coord: float = -0.075,
        y_label_coord2: float = 0,
        bar_texts: list[BarText] = None,
        textboxes: list[dict] = None,
        gridspec_kw: dict = None
) -> None:
    """
    :param filename: Path to output file.
    :param data_list:
    List of List of Data Dict:
    [
        [ {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]},
          {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
        ],
        [ {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]},
          {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
        ],
    ]
    The outer list defines the bars, the inner list the stacks
    :param stack_legend: [optional] Label stacks
    :param bar_legend: [optional] Label bars
    :param xlabel: Large label of x-axis
    :param ylabel: Large label of y-axis
    :param title: Title of whole plot
    :param adjust: [optional] Tuple with 4 values (left, right, top, bottom)
    :param y_log: [optional] Is the first y-scale logarithmic?
    :param x_log: [optional] Is the x-scale logarithmic?
    :param xticks: [optional] Location of x-ticks
    :param xlabels: [optional] Custom x-tick labels
    :param minor_xticks: [optional] Location of minor x-ticks
    :param minor_xlabels: [optional] Text for minor x-ticks
    :param stacks_depend_on_prev: [optional] If true, larger stacks already
        include the size/time/value of smaller ones
    :param colors:  [optional] Custom Bar Colors
    :param hatches:  [optional] Custom hatches
    :param rotate_xticks: [optional] Rotate the x-ticks
    :param backgrounds: [optional] List of tuples (start, end, color)
    :param order: [optional] Reorder Bars
    :param text_boxes: [optional] Text boxes for backgrounds
    :param colors_depend_on_bar:  [optional] Vary colors for Bars not stacks
    :param divide_y: [optional] Use a divided Y-Axis
    :param ymin: [mandatory for divide_y=True] Lower Limit of lower part
    :param ymax: [mandatory for divide_y=True] Upper Limit of lower part
    :param ymin2: [mandatory for divide_y=True] Lower Limit Limit of upper part
    :param ymax2: [mandatory for divide_y=True] Upper Limit of upper part
    :param y_label_coord: [optional] X Position of Y-Axis label
    :param y_label_coord2: [optional] Y Position of Y-Axis label
    :type y_lim: [optional] Custom upper limit
    :param label_step: [optional] Print only every ith step
    :param bar_texts: [optional] Bar texts to add to Bar
    :param gridspec_kw: [optional] Gridspec Values for Y Axis
    :param textboxes: [optional] add arbitrary text boxes
    :return:
    """
    if divide_y:
        # noinspection PyTypeChecker
        fig, (ax1, ax2) = plt.subplots(
            2, 1, sharex=True, gridspec_kw=gridspec_kw)
        # ax2 is lower plot
        if ymin is None or ymax is None or ymin2 is None or ymax2 is None:
            raise RuntimeError(
                "Axis limits need to be defined for divided y axis.")
    else:
        fig, ax1 = plt.subplots()
        ax2 = None

    num_bars = len(data_list)
    num_stacks = len(data_list[0])
    if num_bars == 1:
        bar_width = 0.5
    else:
        bar_width = 0.8 / num_bars
    fat_bars = False
    if len(data_list[0][0].keys()) == 2:
        fat_bars = True
        bar_width = 0.2

    x_values, y_max = [], 0
    bars = []  # Format = bars[bar_num][stack_num][ax_num]
    for k, data in enumerate(data_list):
        # Read Data
        if stack_legend is not None and len(data) != len(stack_legend.labels):
            raise ValueError(
                f"Got data for {len(data)} bars, but legend labels "
                f"for {len(stack_legend.labels)}.")
        num_stacks = len(data)
        x_values = sorted(data[0].keys())
        if order is not None:
            x_values = [x_values[i] for i in order]

        means = {}
        errors = {}
        for i, stack in enumerate(data):
            if set(x_values) != set(stack.keys()):
                raise ValueError(
                    f"Differing X-Values between stack 0 and {i}.")
            for x in x_values:
                m, h = mean_confidence_interval(
                    stack[x]
                )
                if i in means:
                    means[i].append(m)
                    errors[i].append(h)
                else:
                    means[i] = [m]
                    errors[i] = [h]

        ind = [
            (i - (num_bars / 2) * bar_width) + 0.5 * bar_width + k * bar_width
            for i in
            range(len(means[0]))]
        if fat_bars:
            ind = [0.5 + k * 0.2, 1.3 + k * 0.2]
        bottoms = [0 for _ in ind]
        inner_bars = []  # inner_bars[stack_num][ax_num]
        for i in range(num_stacks):
            hatch = None if hatches is None else hatches[i]
            if colors_depend_on_bar:
                color = colors[k]
            else:
                color = colors[i]
            if divide_y:
                axes = [ax1, ax2]
            else:
                axes = [ax1]
            ax_bars = []
            for ax_num, ax in enumerate(axes):
                p = ax.bar(ind, means[i], bar_width, yerr=errors[i],
                           bottom=bottoms,
                           error_kw={
                               'elinewidth': 1,  # Dicke des vertikalen Strichs
                           },
                           color=color,
                           hatch=hatch
                           )
                ax_bars.append(p)
            inner_bars.append(ax_bars)
            if bar_texts is not None:
                add_bar_text(bar_texts, k, i, ax_bars, axes)
            if not stacks_depend_on_prev:
                # noinspection PyUnresolvedReferences
                bottoms = [means[i][j] + bottoms[j] for j in
                           range(len(bottoms))]
                tmp = max(bottoms)
            else:
                tmp = max(means[i])
            y_max = max(tmp, y_max)
        bars.append(inner_bars)
    if textboxes is not None:
        axis = ax1
        # Use lower axis
        for box in textboxes:
            if box['transform'] == 'transAxes':
                box['transform'] = axis.transAxes
            axis.text(**box)
    # Set Axis Labels
    if divide_y:
        ax2.set_xlabel(xlabel)
    else:
        ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    if divide_y:
        ax1.yaxis.set_label_coords(y_label_coord, y_label_coord2)

    # Axis Scaling
    if y_lim is not None:
        ax1.set_ylim(top=y_lim)
    else:
        ax1.set_ylim(top=y_max * y_lim_fac)

    if y_log:
        ax1.set_yscale('log')
    else:
        # Axis Limits
        ax1.set_ylim(bottom=0)

    if divide_y:
        # Limits
        ax1.set_ylim(ymin2, ymax2)  # Upper part
        ax2.set_ylim(ymin, ymax)  # Lower part
        # hide the spines between ax and ax2
        ax1.spines['bottom'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax1.xaxis.tick_top()
        ax1.tick_params(labeltop=False)  # don't put tick labels at the top
        ax2.xaxis.tick_bottom()

    if divide_y:
        xaxis = ax2
    else:
        xaxis = ax1

    if x_log:
        xaxis.set_xscale('log')

    if fat_bars:
        xaxis.set_xlim(left=0, right=2)

    # Axis Ticks
    if xlabels is None:
        xlabels = x_values

    # Only label every second x-tick
    for i in range(0, len(xlabels), 1):
        if i % label_step != 0:
            xlabels[i] = ''

    if fat_bars:
        ind = [0.6, 1.4]
    else:
        ind = [i for i in range(len(x_values))]

    if xticks:
        ind = [ind[i] for i in xticks]

    elif order is not None:
        xlabels = [xlabels[i] for i in order]

    if rotate_xticks:
        xaxis.set_xticks(ind)
        xaxis.set_xticklabels(xlabels,
                              fontdict={'horizontalalignment': 'right',
                                        'rotation': 30})
    else:
        xaxis.set_xticks(ind)
        xaxis.set_xticklabels(xlabels)
    if divide_y:
        ax1.set_xticks(ind)
        # Deactivate Top Ticks altogether
        ax1.tick_params(top=False)

    # Minor Ticks
    set_minor_xticks(xaxis, minor_xticks, minor_xlabels, None, 2)

    # Gray bars
    gray_bars = add_gray_bars(ax1, backgrounds)

    # Text Boxes into gray bars
    add_text_boxes_into_bars(ax1, text_boxes, gray_bars)

    # Divider
    if divide_y:
        # Marks----------------------------------------------------------------
        # -----------------------------------------------------------------------------
        # This looks pretty good, and was fairly painless, but you can get that
        # cut-out diagonal lines look with just a bit more work. The important
        # thing to know here is that in axes coordinates, which are always
        # between 0-1, spine endpoints are at these locations (0,0), (0,1),
        # (1,0), and (1,1).  Thus, we just need to put the diagonals in the
        # appropriate corners of each of our axes, and so long as we use the
        # right transform and disable clipping.

        # Align diagonal lines
        if gridspec_kw is not None and 'height_ratios' in gridspec_kw.keys():
            stretch = (1. * gridspec_kw['height_ratios'][1]) / \
                      gridspec_kw['height_ratios'][0]
        else:
            stretch = 1.0  # Fallback

        d = .015  # how big to make the diagonal lines in axes coordinates
        # arguments to pass to plot, just so we don't keep repeating them
        kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False,
                      linewidth=plt.rcParams['axes.linewidth'])
        ax1.plot((-d, +d), (-(stretch * d), +(stretch * d)),
                 **kwargs)  # top-left diagonal
        ax1.plot((1 - d, 1 + d), (-(stretch * d), +(stretch * d)),
                 **kwargs)  # top-right diagonal

        kwargs.update(transform=ax2.transAxes)  # switch to the bottom axes
        ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # bottom-left diagonal
        ax2.plot((1 - d, 1 + d), (1 - d, 1 + d),
                 **kwargs)  # bottom-right diagonal

        # What's cool about this is that now if we vary the distance between
        # ax and ax2 via f.subplots_adjust(hspace=...) or plt.subplot_tool(),
        # the diagonal lines will move accordingly, and stay right at the tips
        # of the spines they are 'breaking'
        # -----------------------------------------------------------------------------
        # -----------------------------------------------------------------------------

    # Set Title
    if TITLE:
        plt.title(title, y=0.98)

    # Legend
    first_legend = None
    if stack_legend is not None:
        stack_legend.markers = [stack[0][0] for stack in bars[0]]
        stack_legend.axis = ax1
        if stack_legend.location is None:
            stack_legend.location = Legend.TOP
        first_legend = stack_legend.make()

    if bar_legend is not None:
        # for b[i][j][k], i may change based on hatches
        bar_legend.markers = [b[1][0][0] for b in bars]
        bar_legend.axis = ax1
        bar_legend.make()
        if first_legend is not None:
            plt.gca().add_artist(first_legend)

    # Crop
    hspace = 0.15 if divide_y else None
    crop_plot(adjust, figure=fig, hspace=hspace, divider=divide_y)

    output(filename)


def stacked_bar_plot_line(
        filename: str,
        data_list: list[list[dict]],
        line_list: list[dict],
        xlabel: str,
        ylabel: str,
        title: str,
        bar_legend: Legend = None,
        stack_legend: Legend = None,
        adjust: list | tuple = None,
        y_log: bool = False,
        x_log: bool = False,
        xticks: list[int] = None,
        xlabels: list[str] = None,
        minor_xticks: list[int] = None,
        minor_xlabels: list[str] = None,
        stacks_depend_on_prev=False,
        label_step: int = 1,
        colors: list[str] = bar_colors,
        line_colors: list[str] = bar_colors,
        hatches: list[str] = None,
        y_lim: float = None,
        backgrounds: list[tuple] = None,
        text_boxes: list[dict] = tuple(),
        order: list[int] = None,
        rotate_xticks: bool = False,
        colors_depend_on_bar: bool = False,
        bar_texts: list[BarText] = None,
        textboxes: list[dict] = None,
        second_y_axis: bool = True,
        second_y_label: str = None,
        second_ylim: float = None,
        second_y_lim_bottom: int = None,
) -> None:
    """
    :param filename: Path to output file.
    :param data_list:
    List of List of Data Dict:
    [
        [ {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]},
          {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
        ],
        [ {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]},
          {x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
        ],
    ]
    The outer list defines the bars, the inner list the stacks
    :param line_list: List of Data Dicts in the following Format:
        A dict with the X-Values as keys and the Y-Values as a list (even
        if there is only one Y-Value per X-value).
        { x1: [y12, y12, y13], x2: [y21], x3: [y31, y32, y33]}
    :param stack_legend: [optional] Label stacks
    :param bar_legend: [optional] Label bars
    :param xlabel: Large label of x-axis
    :param ylabel: Large label of y-axis
    :param title: Title of whole plot
    :param adjust: [optional] Tuple with 4 values (left, right, top, bottom)
    :param y_log: [optional] Is the first y-scale logarithmic?
    :param x_log: [optional] Is the x-scale logarithmic?
    :param xticks: [optional] Location of x-ticks
    :param xlabels: [optional] Custom x-tick labels
    :param minor_xticks: [optional] Location of minor x-ticks
    :param minor_xlabels: [optional] Text for minor x-ticks
    :param stacks_depend_on_prev: [optional] If true, larger stacks already
        include the size/time/value of smaller ones
    :param colors:  [optional] Custom Bar Colors
    :param hatches:  [optional] Custom hatches
    :param rotate_xticks: [optional] Rotate the x-ticks
    :param backgrounds: [optional] List of tuples (start, end, color)
    :param order: [optional] Reorder Bars
    :param text_boxes: [optional] Text boxes for backgrounds
    :param colors_depend_on_bar:  [optional] Vary colors for Bars not stacks
    :type y_lim: [optional] Custom upper limit
    :param label_step: [optional] Print only every ith step
    :param bar_texts: [optional] Bar texts to add to Bar
    :param textboxes: [optional] add arbitrary text boxes
    :param second_ylim: [optional] Second axis' ylim
    :param second_y_lim_bottom: [optional] Explicit lower limit on second y
    :param second_y_axis: [optional] True if second Y axis
    :param second_y_label: [optional] Label for second Y axis
    """
    fig, ax1 = plt.subplots()
    if second_y_axis is not None:
        ax2 = ax1.twinx()
    else:
        ax2 = None

    num_bars = len(data_list)
    num_stacks = len(data_list[0])
    if num_bars == 1:
        bar_width = 0.5
    else:
        bar_width = 0.8 / num_bars
    fat_bars = False
    if len(data_list[0][0].keys()) == 2:
        fat_bars = True
        bar_width = 0.2


    # Construct value lists
    x_values = sorted(line_list[0].keys())
    y_values = []
    for i, d in enumerate(line_list):
        y_values.append([])
        for x in x_values:
            y_values[i].append(d[x])

    # Compute means and errors.
    y_means = []
    y_errors = []
    for i, d in enumerate(line_list):
        y_means.append([])
        y_errors.append([])
        for y in y_values[i]:
            m, h = mean_confidence_interval(y, 0.95)
            y_means[i].append(m)
            y_errors[i].append(h)

    # Plot
    plts = []
    for i, d in enumerate(line_list):
        plts.append(ax2.errorbar(
            x_values,
            y_means[i],
            yerr=y_errors[i],
            fmt='-', #if fmts is None else fmts[i],
            color=line_colors[i],
            ecolor='black',
            elinewidth=1,  # Dicke des vertikalen Strichs
            barsabove=True,
        ))

    x_values, y_max = [], 0
    bars = []  # Format = bars[bar_num][stack_num][ax_num]
    for k, data in enumerate(data_list):
        # Read Data
        if stack_legend is not None and len(data) != len(stack_legend.labels):
            raise ValueError(
                f"Got data for {len(data)} bars, but legend labels "
                f"for {len(stack_legend.labels)}.")
        num_stacks = len(data)
        x_values = sorted(data[0].keys())
        if order is not None:
            x_values = [x_values[i] for i in order]

        means = {}
        errors = {}
        for i, stack in enumerate(data):
            if set(x_values) != set(stack.keys()):
                raise ValueError(
                    f"Differing X-Values between stack 0 and {i}.")
            for x in x_values:
                m, h = mean_confidence_interval(
                    stack[x]
                )
                if i in means:
                    means[i].append(m)
                    errors[i].append(h)
                else:
                    means[i] = [m]
                    errors[i] = [h]

        ind = [
            (i - (num_bars / 2) * bar_width) + 0.5 * bar_width + k * bar_width
            for i in
            range(len(means[0]))]
        if fat_bars:
            ind = [0.5 + k * 0.2, 1.3 + k * 0.2]
        bottoms = [0 for _ in ind]
        inner_bars = []  # inner_bars[stack_num][ax_num]
        for i in range(num_stacks):
            hatch = None if hatches is None else hatches[i]
            if colors_depend_on_bar:
                color = colors[k]
            else:
                color = colors[i]
            axes = [ax1]
            ax_bars = []
            for ax_num, ax in enumerate(axes):
                p = ax.bar(ind, means[i], bar_width, yerr=errors[i],
                           bottom=bottoms,
                           error_kw={
                               'elinewidth': 1,  # Dicke des vertikalen Strichs
                           },
                           color=color,
                           hatch=hatch
                           )
                ax_bars.append(p)
            inner_bars.append(ax_bars)
            if bar_texts is not None:
                add_bar_text(bar_texts, k, i, ax_bars, axes)
            if not stacks_depend_on_prev:
                # noinspection PyUnresolvedReferences
                bottoms = [means[i][j] + bottoms[j] for j in
                           range(len(bottoms))]
                tmp = max(bottoms)
            else:
                tmp = max(means[i])
            y_max = max(tmp, y_max)
        bars.append(inner_bars)
    if textboxes is not None:
        axis = ax1
        # Use lower axis
        for box in textboxes:
            if box['transform'] == 'transAxes':
                box['transform'] = axis.transAxes
            axis.text(**box)
    # Set Axis Labels
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    if second_y_label:
        ax2.set_ylabel(second_y_label)

    if second_ylim:
        ax2.set_ylim(top=second_ylim)
    if second_y_lim_bottom is not None:
        ax2.set_ylim(bottom=second_y_lim_bottom)

    # Axis Scaling
    if y_lim is not None:
        ax1.set_ylim(top=y_lim)
    else:
        ax1.set_ylim(top=y_max * y_lim_fac)

    if y_log:
        ax1.set_yscale('log')
    else:
        # Axis Limits
        ax1.set_ylim(bottom=0)

    xaxis = ax1

    if x_log:
        xaxis.set_xscale('log')

    if fat_bars:
        xaxis.set_xlim(left=0, right=2)

    # Axis Ticks
    if xlabels is None:
        xlabels = x_values

    # Only label every second x-tick
    for i in range(0, len(xlabels), 1):
        if i % label_step != 0:
            xlabels[i] = ''

    if fat_bars:
        ind = [0.6, 1.4]
    else:
        ind = [i for i in range(len(x_values))]

    if xticks:
        ind = [ind[i] for i in xticks]

    elif order is not None:
        xlabels = [xlabels[i] for i in order]

    if rotate_xticks:
        xaxis.set_xticks(ind)
        xaxis.set_xticklabels(xlabels,
                              fontdict={'horizontalalignment': 'right',
                                        'rotation': 30})
    else:
        xaxis.set_xticks(ind)
        xaxis.set_xticklabels(xlabels)

    # Minor Ticks
    set_minor_xticks(xaxis, minor_xticks, minor_xlabels, None, 2)

    # Gray bars
    gray_bars = add_gray_bars(ax1, backgrounds)

    # Text Boxes into gray bars
    add_text_boxes_into_bars(ax1, text_boxes, gray_bars)

    # Set Title
    if TITLE:
        plt.title(title, y=0.98)

    # Legend
    first_legend = None
    if stack_legend is not None:
        stack_legend.markers = [stack[0][0] for stack in bars[0]]
        stack_legend.axis = ax1
        if stack_legend.location is None:
            stack_legend.location = Legend.TOP
        first_legend = stack_legend.make()

    if bar_legend is not None:
        bar_legend.markers = [b[0][0][0] for b in bars]
        bar_legend.axis = ax1
        bar_legend.make()
        if first_legend is not None:
            plt.gca().add_artist(first_legend)

    for pos in ['right', 'top', 'bottom', 'left']:
        ax2.spines[pos].set_visible(False)
    crop_plot(adjust, figure=fig)

    output(filename)
