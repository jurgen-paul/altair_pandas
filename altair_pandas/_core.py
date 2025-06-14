import warnings

import altair as alt
import pandas as pd
import numpy as np


def _valid_column(column_name):
    """Return a valid column name."""
    return str(column_name)


def _get_fontsize(size_name):
    """Return a fontsize based on matplotlib labels."""
    font_sizes = {
        "xx-small": 5.79,
        "x-small": 6.94,
        "small": 8.33,
        "medium": 10.0,
        "large": 12.0,
        "x-large": 14.4,
        "xx-large": 17.28,
        "larger": 12.0,
        "smaller": 8.33,
    }
    return font_sizes[size_name]


def _get_layout(panels, layout=None):
    """Compute the layout for a gridded chart.

    Parameters
    ----------
    panels : int
        Number of panels in the chart.
    layout : tuple of ints
        Control the layout. Negative entries will be inferred
        from the number of panels.

    Returns
    -------
    nrows, ncols : int, int
        number of rows and columns in the resulting layout.

    Examples
    --------
    >>> _get_layout(6, (2, 3))
    (2, 3)
    >>> _get_layout(6, (1, -1))
    (1, 6)
    >>> _get_layout(6, (-1, 2))
    (3, 2)
    """
    if layout is None:
        layout = (-1, 2)
    if len(layout) != 2:
        raise ValueError("layout should have two elements")
    if layout[0] < 0 and layout[1] < 0:
        raise ValueError("At least one dimension of layout must be positive")
    if layout[0] < 0:
        layout = (int(np.ceil(panels / layout[1])), layout[1])
    if layout[1] < 0:
        layout = (layout[0], int(np.ceil(panels / layout[0])))
    if panels > layout[0] * layout[1]:
        raise ValueError(f"layout {layout[0]}x{layout[1]} must be larger than {panels}")
    return layout


class _PandasPlotter:
    """Base class for pandas plotting."""

    @classmethod
    def create(cls, data):
        if isinstance(data, pd.Series):
            return _SeriesPlotter(data)
        elif isinstance(data, pd.DataFrame):
            return _DataFramePlotter(data)
        else:
            raise NotImplementedError(f"data of type {type(data)}")

    def _get_mark_def(self, mark, kwargs):
        if isinstance(mark, str):
            mark = {"type": mark}
        if isinstance(kwargs.get("alpha"), float):
            mark["opacity"] = kwargs.pop("alpha")
        if isinstance(kwargs.get("color"), str):
            mark["color"] = kwargs.pop("color")
        return mark

    def _kde(self, data, bw_method=None, ind=None, **kwargs):
        if bw_method == "scott" or bw_method is None:
            bandwidth = 0
        elif bw_method == "silverman":
            # Implementation taken from
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html
            n = data.shape[0]
            d = 1
            bandwidth = (n * (d + 2) / 4.0) ** (-1.0 / (d + 4))
        elif callable(bw_method):
            if 1 < data.shape[1]:
                warnings.warn(
                    "Using a callable argument for ind using the Altair"
                    " plotting backend sets the bandwidth for all"
                    " columns",
                    category=UserWarning,
                )
            bandwidth = bw_method(data)
        else:
            bandwidth = bw_method

        if ind is None:
            steps = 1_000
        elif isinstance(ind, np.ndarray):
            warnings.warn(
                "The Altair plotting backend does not support sequences for ind",
                category=UserWarning,
            )
            steps = 1_000
        else:
            steps = ind

        chart = (
            alt.Chart(data, mark=self._get_mark_def("area", kwargs))
            .transform_fold(
                data.columns.to_numpy(),
                as_=["Column", "value"],
            )
            .transform_density(
                density="value",
                bandwidth=bandwidth,
                groupby=["Column"],
                # Manually setting domain to min and max makes kde look
                # more uniform
                extent=[data.min().min(), data.max().max()],
                steps=steps,
            )
            .encode(
                x=alt.X("value", type="quantitative"),
                y=alt.Y("density", type="quantitative", stack="zero"),
                tooltip=[
                    alt.Tooltip("value", type="quantitative"),
                    alt.Tooltip("density", type="quantitative"),
                    alt.Tooltip("Column", type="nominal"),
                ],
            )
            .interactive()
        )
        # If there is only one column, do not encode color so that user
        # can pass optional color kwarg into mark
        if 1 < data.shape[1]:
            chart = chart.encode(color=alt.Color("Column", type="nominal"))
        return chart


class _SeriesPlotter(_PandasPlotter):
    """Functionality for plotting of pandas Series."""

    def __init__(self, data):
        if not isinstance(data, pd.Series):
            raise ValueError(f"data: expected pd.Series; got {type(data)}")
        self._data = data

    def _preprocess_data(self, with_index=True):
        # TODO: do this without copy?
        data = self._data
        if with_index:
            if isinstance(data.index, pd.MultiIndex):
                data = data.copy()
                data.index = pd.Index(
                    [str(i) for i in data.index], name=data.index.name
                )
            data = data.reset_index()
        else:
            data = data.to_frame()
        # Column names must all be strings.
        return data.rename(columns=_valid_column)

    def _xy(self, mark, **kwargs):
        data = self._preprocess_data(with_index=True)
        return (
            alt.Chart(data, mark=self._get_mark_def(mark, kwargs))
            .encode(
                x=alt.X(data.columns[0], title=None),
                y=alt.Y(data.columns[1], title=None),
                tooltip=list(data.columns),
            )
            .interactive()
        )

    def line(self, **kwargs):
        return self._xy("line", **kwargs)

    def bar(self, **kwargs):
        return self._xy({"type": "bar", "orient": "vertical"}, **kwargs)

    def barh(self, **kwargs):
        chart = self._xy({"type": "bar", "orient": "horizontal"}, **kwargs)
        chart.encoding.x, chart.encoding.y = chart.encoding.y, chart.encoding.x
        return chart

    def area(self, **kwargs):
        return self._xy(mark="area", **kwargs)

    def scatter(self, **kwargs):
        raise ValueError("kind='scatter' can only be used for DataFrames.")

    def hist(self, bins=None, orientation="vertical", **kwargs):
        data = self._preprocess_data(with_index=False)
        column = data.columns[0]
        if isinstance(bins, int):
            bins = alt.Bin(maxbins=bins)
        elif bins is None:
            bins = True
        if orientation == "vertical":
            Indep, Dep = alt.X, alt.Y
        elif orientation == "horizontal":
            Indep, Dep = alt.Y, alt.X
        else:
            raise ValueError("orientation must be 'horizontal' or 'vertical'.")

        mark = self._get_mark_def({"type": "bar", "orient": orientation}, kwargs)
        return alt.Chart(data, mark=mark).encode(
            Indep(column, title=None, bin=bins), Dep("count()", title="Frequency")
        )

    def hist_series(self, **kwargs):
        return self.hist(**kwargs)

    def box(self, vert=True, **kwargs):
        data = self._preprocess_data(with_index=False)
        chart = (
            alt.Chart(data)
            .transform_fold(list(data.columns), as_=["column", "value"])
            .mark_boxplot()
            .encode(x=alt.X("column:N", title=None), y="value:Q")
        )
        if not vert:
            chart.encoding.x, chart.encoding.y = chart.encoding.y, chart.encoding.x
        return chart

    def kde(self, bw_method=None, ind=None, **kwargs):
        data = self._preprocess_data(with_index=False)
        return self._kde(data, bw_method=bw_method, ind=ind, **kwargs)


class _DataFramePlotter(_PandasPlotter):
    """Functionality for plotting of pandas DataFrames."""

    def __init__(self, data):
        if not isinstance(data, pd.DataFrame):
            raise ValueError(f"data: expected pd.DataFrame; got {type(data)}")
        self._data = data

    def _preprocess_data(self, with_index=True, usecols=None):
        data = self._data.rename(columns=_valid_column)
        if usecols is not None:
            data = data[usecols]
        if with_index:
            if isinstance(data.index, pd.MultiIndex):
                data.index = pd.Index(
                    [str(i) for i in data.index], name=data.index.name
                )
            return data.reset_index()
        return data

    def _xy(self, mark, x=None, y=None, stacked=False, subplots=False, **kwargs):
        data = self._preprocess_data(with_index=True)

        if x is None:
            x = data.columns[0]
        else:
            x = _valid_column(x)
            assert x in data.columns

        if y is None:
            y_values = list(data.columns[1:])
        else:
            y = _valid_column(y)
            assert y in data.columns
            y_values = [y]

        chart = (
            alt.Chart(data, mark=self._get_mark_def(mark, kwargs))
            .transform_fold(y_values, as_=["column", "value"])
            .encode(
                x=x,
                y=alt.Y("value:Q", title=None, stack=stacked),
                color=alt.Color("column:N", title=None),
                tooltip=[x] + y_values,
            )
            .interactive()
        )

        if subplots:
            nrows, ncols = _get_layout(len(y_values), kwargs.get("layout", (-1, 1)))
            chart = chart.encode(facet=alt.Facet("column:N", title=None)).properties(
                columns=ncols
            )

        return chart

    def line(self, x=None, y=None, **kwargs):
        return self._xy("line", x, y, **kwargs)

    def area(self, x=None, y=None, stacked=True, **kwargs):
        mark = "area" if stacked else {"type": "area", "line": True, "opacity": 0.5}
        return self._xy(mark, x, y, stacked, **kwargs)

    # TODO: bars should be grouped, not stacked.
    def bar(self, x=None, y=None, **kwargs):
        return self._xy({"type": "bar", "orient": "vertical"}, x, y, **kwargs)

    def barh(self, x=None, y=None, **kwargs):
        chart = self._xy({"type": "bar", "orient": "horizontal"}, x, y, **kwargs)
        chart.encoding.x, chart.encoding.y = chart.encoding.y, chart.encoding.x
        return chart

    def scatter(self, x, y, c=None, s=None, **kwargs):
        if x is None or y is None:
            raise ValueError("kind='scatter' requires 'x' and 'y' arguments.")
        encodings = {"x": _valid_column(x), "y": _valid_column(y)}
        if c is not None:
            encodings["color"] = _valid_column(c)
        if s is not None:
            encodings["size"] = _valid_column(s)
        columns = list(set(encodings.values()))
        data = self._preprocess_data(with_index=False, usecols=columns)
        encodings["tooltip"] = columns
        mark = self._get_mark_def("point", kwargs)
        return alt.Chart(data, mark=mark).encode(**encodings).interactive()

    def hist(self, bins=None, stacked=None, orientation="vertical", **kwargs):
        data = self._preprocess_data(with_index=False)
        if isinstance(bins, int):
            bins = alt.Bin(maxbins=bins)
        elif bins is None:
            bins = True
        if orientation == "vertical":
            Indep, Dep = alt.X, alt.Y
        elif orientation == "horizontal":
            Indep, Dep = alt.Y, alt.X
        else:
            raise ValueError("orientation must be 'horizontal' or 'vertical'.")

        mark = self._get_mark_def({"type": "bar", "orient": orientation}, kwargs)
        chart = (
            alt.Chart(data, mark=mark)
            .transform_fold(list(data.columns), as_=["column", "value"])
            .encode(
                Indep("value:Q", title=None, bin=bins),
                Dep("count()", title="Frequency", stack=stacked),
                color="column:N",
            )
        )

        if kwargs.get("subplots"):
            nrows, ncols = _get_layout(data.shape[1], kwargs.get("layout", (-1, 1)))
            chart = chart.encode(facet=alt.Facet("column:N", title=None)).properties(
                columns=ncols
            )

        return chart

    def hist_frame(self, column=None, layout=(-1, 2), **kwargs):
        if column is not None:
            if isinstance(column, str):
                column = [column]
        data = self._preprocess_data(with_index=False, usecols=column)
        data = data._get_numeric_data()
        nrows, ncols = _get_layout(data.shape[1], layout)
        return (
            alt.Chart(data, mark=self._get_mark_def("bar", kwargs))
            .encode(
                x=alt.X(alt.repeat("repeat"), type="quantitative", bin=True),
                y=alt.Y("count()", title="Frequency"),
            )
            .repeat(repeat=list(data.columns), columns=ncols)
        )

    def box(
        self,
        vert=True,
        column=None,
        by=None,
        fontsize=None,
        rot=0,
        grid=True,
        figsize=None,
        layout=None,
        return_type=None,
        **kwargs,
    ):
        data = self._preprocess_data(with_index=False)

        if column is not None:
            columns = [column] if isinstance(column, str) else column
        else:
            columns = data.select_dtypes(np.number).columns
            if by is not None:
                columns = columns.difference(pd.Index(list(by)))

        if by is not None:
            if np.iterable(by) and not isinstance(by, str) and 1 < len(by):
                by_identifier = ", ".join(by)
                by_title = f"[{by_identifier}]"
                # Check that name doesn't overlap with existing
                # columns
                # If it does, assign a unique name
                by_column = (
                    by_identifier if by_identifier not in columns else "".join(columns)
                )
                data[by_column] = data[by].apply(
                    lambda row: f"({', '.join(row)})", axis=1
                )
                panels = data[by_column].nunique()
            else:
                by = by.pop() if not isinstance(by, str) else by
                panels = data[by].nunique()
                by_title = by
                by_column = by
            x_column = by_column
            x_title = by_title
        else:
            panels = 1
            x_column = "Column"
            x_title = None

        mark_args = {
            kwarg: value
            for kwarg, value in kwargs.items()
            if kwarg in {"alpha", "color"}
        }

        # Matplotlib measures counterclockwise, while Vega-Lite measures
        # clockwise
        # Convert counterclockwise to clockwise
        label_angle = 360 - rot

        if return_type is not None:
            warnings.warn(
                "Different return types are not implimented for the Altair backend.",
                category=UserWarning,
            )

        _, n_columns = _get_layout(panels, layout=layout)

        chart = (
            alt.Chart(data)
            .transform_fold(list(columns), as_=["Column", "Value"])
            .mark_boxplot(**mark_args)
            .encode(
                x=alt.X(
                    x_column,
                    title=x_title,
                    type="nominal",
                    axis=alt.Axis(labelAngle=label_angle, grid=grid),
                ),
                y=alt.Y("Value", type="quantitative", axis=alt.Axis(grid=grid)),
                tooltip=[
                    alt.Tooltip(x_column, title=x_title, type="nominal"),
                    alt.Tooltip("Value", type="quantitative"),
                ],
            )
            .interactive()
        )

        if not vert:
            chart.encoding.x, chart.encoding.y = chart.encoding.y, chart.encoding.x

        if by is not None:
            chart = chart.facet(
                facet=alt.Facet("Column", title=None, type="nominal"),
                columns=n_columns,
            ).properties(title=f"Boxplot grouped by {by}")

        if fontsize is not None:
            size = _get_fontsize(fontsize) if isinstance(fontsize, str) else fontsize
            chart = chart.configure_axis(
                labelFontSize=size,
                titleFontSize=size,
            )

        if figsize is not None:
            width, height = figsize
            chart = chart.configure_view(
                continuousHeight=height,
                discreteHeight=height,
                continuousWidth=width,
                discreteWidth=width,
            )

        return chart

    def kde(self, bw_method=None, ind=None, **kwargs):
        data = self._preprocess_data(with_index=False)
        return self._kde(data, bw_method=bw_method, ind=ind, **kwargs)

    def hexbin(self, x, y, C=None, reduce_C_function=None, gridsize=None, **kwargs):
        data = self._preprocess_data(with_index=False)

        if np.iterable(gridsize):
            x_bins, y_bins = gridsize
        else:
            x_bins = 100 if gridsize is None else gridsize
            # Since rectangles are being used here,
            # instead of hexagons like in Matplotlib,
            # set default y_bins equal to x_bins
            y_bins = x_bins

        x_step = (data[x].max() - data[x].min()) / x_bins
        y_step = (data[y].max() - data[y].min()) / y_bins

        # Default set to bluegreen to match Matplotlib's default
        color_scheme = kwargs.pop("cmap", "bluegreen")

        if C is not None:
            reduce_C_function = (
                np.mean if reduce_C_function is None else reduce_C_function
            )
            # Make sure column is not overwritten if C is one
            # of the coordinate columns
            color_shorthand = C if C not in (x, y) else f"reduced_{C}"
            data[color_shorthand] = data.groupby(
                [
                    pd.cut(data[x], bins=x_bins),
                    pd.cut(data[y], bins=y_bins),
                ]
            )[C].transform(reduce_C_function)
            # All reduced values will be identical across rows that
            # belong to the same bin
            # Since the median of a collection of identical values is
            # the value itself, the median is used here as a way to pass
            # the reduced value per bin to Altair
            color_aggregate = "median"
            color_title = C
        else:
            color_shorthand = x
            color_aggregate = "count"
            color_title = "Count"

        chart = (
            alt.Chart(data)
            .mark_rect(**kwargs)
            .encode(
                x=alt.X(x, bin=alt.Bin(step=x_step)),
                y=alt.Y(y, bin=alt.Bin(step=y_step)),
                color=alt.Color(
                    color_shorthand,
                    aggregate=color_aggregate,
                    scale=alt.Scale(scheme=color_scheme),
                    title=color_title,
                    type="quantitative",
                ),
                tooltip=[
                    alt.Tooltip(x, bin=alt.Bin(step=x_step), type="quantitative"),
                    alt.Tooltip(y, bin=alt.Bin(step=y_step), type="quantitative"),
                    alt.Tooltip(
                        color_shorthand,
                        aggregate=color_aggregate,
                        title=color_title,
                        type="quantitative",
                    ),
                ],
            )
            .interactive()
        )

        return chart


def plot(data, kind="line", **kwargs):
    """Pandas plotting interface for Altair."""
    plotter = _PandasPlotter.create(data)

    if hasattr(plotter, kind):
        plotfunc = getattr(plotter, kind)
    else:
        raise NotImplementedError(f"kind='{kind}' for data of type {type(data)}")

    return plotfunc(**kwargs)


def hist_frame(data, **kwargs):
    return _PandasPlotter.create(data).hist_frame(**kwargs)


def hist_series(data, **kwargs):
    return _PandasPlotter.create(data).hist_series(**kwargs)


def boxplot_frame(
    data,
    column=None,
    by=None,
    fontsize=None,
    rot=0,
    grid=True,
    figsize=None,
    layout=None,
    return_type=None,
    **kwargs,
):
    return _PandasPlotter.create(data).box(
        column=column,
        by=by,
        fontsize=fontsize,
        rot=rot,
        grid=grid,
        figsize=figsize,
        layout=layout,
        return_type=return_type,
        **kwargs,
    )
