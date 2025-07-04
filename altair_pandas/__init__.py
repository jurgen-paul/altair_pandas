"""Altair plotting extension for pandas."""
__version__ = "0.1.0dev0"
__all__ = ["boxplot_frame", "plot", "hist_frame", "hist_series", "scatter_matrix"]

from ._core import boxplot_frame, plot, hist_frame, hist_series
from ._misc import scatter_matrix
