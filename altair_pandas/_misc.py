import altair as alt
from typing import Union, List

toltipList = List[alt.Tooltip]


def scatter_matrix(
    df,
    color: Union[str, None] = None,
    alpha: float = 1.0,
    tooltip: Union[List[str], toltipList, None] = None,
    **kwargs
):
    """ plots a scatter matrix

    At the moment does not support neither histogram nor kde;
    Uses f-f scatterplots instead. Interactive and with a cusotmizable
    tooltip

    Parameters
    ----------
    df : DataFame
        DataFame to be used for scatterplot. Only numeric columns will be included.
    color : string [optional]
        Can be a column name or specific color value (hex, webcolors).
    alpha : float
        Opacity of the markers, within [0,1]
    tooltip: list [optional]
        List of specific column names or alt.Tooltip objects. If none (default),
        will show all columns.
    """
    dfc = df.rename(columns=str).copy()  # otherwise passing array will be preserved
    cols = dfc._get_numeric_data().columns.tolist()

    chart = (
        alt.Chart(dfc)
        .mark_circle()
        .encode(
            x=alt.X(alt.repeat("column"), type="quantitative"),
            y=alt.X(alt.repeat("row"), type="quantitative"),
            opacity=alt.value(alpha),
            tooltip=tooltip or dfc.columns.tolist(),
        )
        .properties(width=150, height=150)
    )

    if color:
        color = str(color)

        if color in dfc:
            color = alt.Color(color)
            if "colormap" in kwargs:
                color.scale = alt.Scale(scheme=kwargs.get("colormap"))
        else:
            color = alt.value(color)
        chart = chart.encode(color=color)

    return chart.repeat(row=cols, column=cols).interactive()
