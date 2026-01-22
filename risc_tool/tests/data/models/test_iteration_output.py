import pandas as pd

from risc_tool.data.models.iteration_output import IterationOutput


def test_iteration_output_creation():
    io = IterationOutput(
        risk_segment_column=pd.Series([1, 2, 3]),
        errors=["err1"],
        warnings=["warn1"],
        invalid_groups=[99],
    )
    assert len(io.risk_segment_column) == 3
    assert io.errors == ["err1"]
    assert io.warnings == ["warn1"]
    assert io.invalid_groups == [99]
