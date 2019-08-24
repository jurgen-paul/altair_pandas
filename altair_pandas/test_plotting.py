import pytest
import pandas as pd


@pytest.fixture
def series():
    return pd.Series(range(5), name='data_name')


@pytest.fixture
def dataframe():
    return pd.DataFrame({'x': range(5), 'y': range(5)})


series_cases = {
    'line': {
        'answer': {
            'mark': 'line',
            'encoding_x': 'index',
            'encoding_y': 'data_name'
        }
    },

    'bar': {
        'answer': {
            'mark': 'bar',
            'encoding_x': 'index',
            'encoding_y': 'data_name'
        }
    },

    'area': {
        'answer': {
            'mark': 'area',
            'encoding_x': 'index',
            'encoding_y': 'data_name'
        }
    }
}

@pytest.mark.parametrize('kind, props', series_cases.items())
def test_series_plot(series, with_plotting_backend, kind, props):
    chart = series.plot(kind=kind)
    spec = chart.to_dict()

    answer = props['answer']

    assert spec['mark'] == answer['mark']
    assert spec['encoding']['x']['field'] == answer['encoding_x']
    assert spec['encoding']['y']['field'] == answer['encoding_y']


dataframe_cases = {
    'line': {
        'answer': {
            'mark': 'line',
            'encoding_x': 'index',
            'encoding_y': 'value'
        }
    },

    'bar': {
        'answer': {
            'mark': 'bar',
            'encoding_x': 'index',
            'encoding_y': 'value'
        }
    },

    'area': {
        'answer': {
            'mark': 'area',
            'encoding_x': 'index',
            'encoding_y': 'value'
        }
    }
}

@pytest.mark.parametrize('kind, props', dataframe_cases.items())
def test_dataframe_plot(dataframe, with_plotting_backend, kind, props):
    chart = dataframe.plot(kind=kind)
    spec = chart.to_dict()

    answer = props['answer']
    assert spec['mark'] == answer['mark']
    assert spec['encoding']['x']['field'] == answer['encoding_x']
    assert spec['encoding']['y']['field'] == answer['encoding_y']
    assert spec['encoding']['color']['field'] == 'column'
    assert spec['transform'][0]['fold'] == ['x', 'y']
