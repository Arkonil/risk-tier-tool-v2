from risc_tool.data.models.enums import LossRateTypes
from risc_tool.data.models.iteration_metadata import IterationMetadata
from risc_tool.data.models.types import MetricID


def test_iteration_metadata_update():
    meta = IterationMetadata(
        editable=True,
        scalars_enabled=False,
        split_view_enabled=False,
        show_prev_iter_details=False,
        loss_rate_type=LossRateTypes.DLR,
        initial_filter_ids=[],
        current_filter_ids=[],
        metric_ids=[],
    )

    meta.update(editable=False, loss_rate_type=LossRateTypes.ULR)

    assert meta.editable is False
    assert meta.loss_rate_type == LossRateTypes.ULR
    assert meta.scalars_enabled is False  # Unchanged


def test_iteration_metadata_with_changes():
    meta = IterationMetadata(
        editable=True,
        scalars_enabled=False,
        split_view_enabled=False,
        show_prev_iter_details=False,
        loss_rate_type=LossRateTypes.DLR,
        initial_filter_ids=[],
        current_filter_ids=[],
        metric_ids=[MetricID.VOLUME],
    )

    new_meta = meta.with_changes(scalars_enabled=True)

    assert new_meta is not meta
    assert new_meta.scalars_enabled is True
    # Others copied
    assert new_meta.editable is True
    assert new_meta.metric_ids == [MetricID.VOLUME]

    # Original unchanged
    assert meta.scalars_enabled is False


def test_properties(meta=None):
    if meta is None:
        meta = IterationMetadata(
            editable=True,
            scalars_enabled=False,
            split_view_enabled=False,
            show_prev_iter_details=False,
            loss_rate_type=LossRateTypes.DLR,
            initial_filter_ids=[],
            current_filter_ids=[],
            metric_ids=[],
        )
    props = meta.properties
    assert "editable" in props
    assert "loss_rate_type" in props
