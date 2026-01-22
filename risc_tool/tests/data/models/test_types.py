from risc_tool.data.models.types import DataSourceID, FilterID, IterationID, MetricID


def test_datasource_id_sentinels():
    assert int(DataSourceID.TEMPORARY) == -1
    assert int(DataSourceID.EMPTY) == -2
    assert repr(DataSourceID.TEMPORARY) == "<TEMPORARY>"


def test_metric_id_sentinels():
    assert int(MetricID.VOLUME) == -2
    assert repr(MetricID.UNT_BAD_RATE) == "<UNT_BAD_RATE>"


def test_filter_id_sentinels():
    assert int(FilterID.TEMPORARY) == -1


def test_iteration_id_sentinels():
    assert int(IterationID.INVALID) == -1
