from ._core import hist, scatterplot
import altair as alt
import pandas as pd


def scatter_matrix(df, alpha: float = 0.2, diagonal: str = "kde"):
    """ plots a scatter matrix

    at the moment does not support neither histogram nor kde;
    Uses f-f scatterplots instead
    
    """
    cols = df._get_numeric_data().columns.astype(str).tolist()

    # if diagonal == "kde":
    #     pass
    # elif diagonal == "hist":
    #     pass
    # else:
    #     raise ValueError(f"diagonal should be either `kde` or `hist`, got `{diagonal}`")

    chart = (
        alt.Chart(df)
        .mark_circle()
        .encode(
            x=alt.X(alt.repeat("column"), type="quantitative"),
            y=alt.X(alt.repeat("row"), type="quantitative"),
        )
        .properties(width=150, height=150, opacity=alpha)
        .repeat(rows=cols, columns=cols)
        .interactive()
    )

    return chart
