import pytest
import numpy as np
import pandas as pd
import altair as alt


@pytest.fixture
def series():
    return pd.Series(range(5), name='data_name')


@pytest.fixture
def dataframe():
    return pd.DataFrame({'x': range(5), 'y': range(5)})


@pytest.mark.parametrize('data', [
    pd.Series(
        range(6),
        index=pd.MultiIndex.from_product([['a', 'b', 'c'], [1, 2]])
    ),
    pd.DataFrame(
        {'x': range(6)},
        index=pd.MultiIndex.from_product([['a', 'b', 'c'], [1, 2]])
    )
])
def test_multiindex(data, with_plotting_backend):
    chart = data.plot.bar()
    spec = chart.to_dict()
    assert list(chart.data.iloc[:, 0]) == [str(i) for i in data.index]
    assert spec['encoding']['x']['field'] == 'index'
    assert spec['encoding']['x']['type'] == 'nominal'


def test_nonstring_column_names(with_plotting_backend):
    data = pd.DataFrame(np.ones((3, 4)))
    chart = data.plot.scatter(x=0, y=1, c=2, s=3)

    # Ensure data is not modified
    assert list(data.columns) == list(range(4))
    # Ensure chart data has string columns
    assert set(chart.data.columns) == {str(i) for i in range(4)}

    spec = chart.to_dict()
    assert spec['encoding']['x']['field'] == '0'
    assert spec['encoding']['y']['field'] == '1'
    assert spec['encoding']['color']['field'] == '2'
    assert spec['encoding']['size']['field'] == '3'


@pytest.mark.parametrize('kind', ['line', 'area', 'bar'])
def test_series_basic_plot(series, kind, with_plotting_backend):
    chart = series.plot(kind=kind)
    spec = chart.to_dict()
    if kind == 'bar':
        assert spec['mark'] == {'type': 'bar', 'orient': 'vertical'}
    else:
        assert spec['mark'] == kind
    assert spec['encoding']['x']['field'] == 'index'
    assert spec['encoding']['y']['field'] == 'data_name'


@pytest.mark.parametrize('kind', ['line', 'area', 'bar'])
def test_dataframe_basic_plot(dataframe, kind, with_plotting_backend):
    chart = dataframe.plot(kind=kind)
    spec = chart.to_dict()
    if kind == 'bar':
        assert spec['mark'] == {'type': 'bar', 'orient': 'vertical'}
    else:
        assert spec['mark'] == kind
    assert spec['encoding']['x']['field'] == 'index'
    assert spec['encoding']['y']['field'] == 'value'
    assert spec['encoding']['color']['field'] == 'column'
    assert spec['transform'][0]['fold'] == ['x', 'y']


def test_series_barh(series, with_plotting_backend):
    chart = series.plot.barh()
    spec = chart.to_dict()
    assert spec['mark'] == {'type': 'bar', 'orient': 'horizontal'}
    assert spec['encoding']['y']['field'] == 'index'
    assert spec['encoding']['x']['field'] == 'data_name'


def test_dataframe_barh(dataframe, with_plotting_backend):
    chart = dataframe.plot.barh()
    spec = chart.to_dict()
    assert spec['mark'] == {'type': 'bar', 'orient': 'horizontal'}
    assert spec['encoding']['y']['field'] == 'index'
    assert spec['encoding']['x']['field'] == 'value'
    assert spec['encoding']['color']['field'] == 'column'
    assert spec['transform'][0]['fold'] == ['x', 'y']


def test_series_scatter_plot(series, with_plotting_backend):
    with pytest.raises(ValueError):
        series.plot.scatter('x', 'y')


def test_dataframe_scatter_plot(dataframe, with_plotting_backend):
    dataframe['c'] = range(len(dataframe))
    chart = dataframe.plot.scatter('x', 'y', c='y', s='x')
    spec = chart.to_dict()
    assert spec['mark'] == 'point'
    assert spec['encoding']['x']['field'] == 'x'
    assert spec['encoding']['y']['field'] == 'y'
    assert spec['encoding']['color']['field'] == 'y'
    assert spec['encoding']['size']['field'] == 'x'


@pytest.mark.parametrize('bins', [None, 10])
def test_series_hist(series, bins, with_plotting_backend):
    chart = series.plot.hist(bins=bins)
    spec = chart.to_dict()
    assert spec['mark'] == 'bar'
    assert spec['encoding']['x']['field'] == 'data_name'
    assert 'field' not in spec['encoding']['y']
    exp_bin = True if bins is None else {'maxbins': bins}
    assert spec['encoding']['x']['bin'] == exp_bin


@pytest.mark.parametrize('bins', [None, 10])
@pytest.mark.parametrize('stacked', [None, True, False])
def test_dataframe_hist(dataframe, bins, stacked, with_plotting_backend):
    chart = dataframe.plot.hist(bins=bins, stacked=stacked)
    spec = chart.to_dict()
    assert spec['mark'] == 'bar'
    assert spec['encoding']['x']['field'] == 'value'
    assert 'field' not in spec['encoding']['y']
    assert spec['encoding']['color']['field'] == 'column'
    assert spec['transform'][0]['fold'] == ['x', 'y']
    exp_bin = True if bins is None else {'maxbins': bins}
    assert spec['encoding']['x']['bin'] == exp_bin
    assert spec['encoding']['y']['stack'] == (True if stacked else stacked)


def test_series_boxplot(series, with_plotting_backend):
    chart = series.plot.box()
    spec = chart.to_dict()
    assert spec['mark'] == 'boxplot'
    assert spec['encoding']['x']['field'] == 'column'
    assert spec['encoding']['y']['field'] == 'value'
    assert spec['transform'][0]['fold'] == ['data_name']


def test_dataframe_boxplot(dataframe, with_plotting_backend):
    chart = dataframe.plot.box()
    spec = chart.to_dict()
    assert spec['mark'] == 'boxplot'
    assert spec['encoding']['x']['field'] == 'column'
    assert spec['encoding']['y']['field'] == 'value'
    assert spec['transform'][0]['fold'] == ['x', 'y']


@pytest.mark.parametrize('props', [
    {'title': 'Test Title', 'color': 'y', 'alpha': 0.2},
    {'title': 'Test Title', 'color': 'purple', 'alpha': 'y'},
    {'title': 'Test Title', 'color': 'purple', 'alpha': 'y'},
    {'title': 'Test Title', 'color': 'purple', 'alpha': 'y'},
    {'title': 'Test Title',
     'color': alt.Color('y', scale=alt.Scale(scheme='viridis')),
     'alpha': 0.2}
    ])
def test_additional_properties(dataframe, props, with_plotting_backend):
    chart = dataframe.plot.barh(**props)
    spec = chart.to_dict()

    assert spec['title'] == props['title']

    if props['alpha'] == 0.2:
        assert spec['encoding']['opacity'] == alt.value(props['alpha'])
    else:
        assert spec['encoding']['opacity'] == {'field': props['alpha'],
                                               'type': 'quantitative'}

    if props['color'] == 'purple':
        assert spec['encoding']['color'] == alt.value(props['color'])
    elif isinstance(props['color'], alt.Color):
        assert spec['encoding']['color'] == props['color'].to_dict()
    else:
        assert spec['encoding']['color'] == {'field': props['color'],
                                             'type': 'quantitative'}
