import numpy as np
import pandas as pd

from risc_tool.data.models.enums import LossRateTypes, RSDetCol
from risc_tool.data.models.iteration_metadata import IterationMetadata
from risc_tool.data.models.singleton import Singleton
from risc_tool.data.models.types import MetricID


class DefaultOptions(Singleton):
    def __init__(self):
        self.__risk_segment_details = pd.DataFrame(
            [
                ["1A", 0, 0.02, "#3D8F3D", "#FFFFFF", 1.3, 1.3],
                ["1B", 0, 0.02, "#3D8F3D", "#FFFFFF", 1.3, 1.3],
                ["2A", 0.02, 0.04, "#7D9438", "#FFFFFF", 1.15, 1.15],
                ["2B", 0.02, 0.04, "#7D9438", "#FFFFFF", 1.15, 1.15],
                ["3A", 0.04, 0.07, "#948238", "#FFFFFF", 1.0, 1.0],
                ["3B", 0.04, 0.07, "#948238", "#FFFFFF", 1.0, 1.0],
                ["4A", 0.07, 0.1, "#8F663D", "#FFFFFF", 0.9, 0.9],
                ["4B", 0.07, 0.1, "#8F663D", "#FFFFFF", 0.9, 0.9],
                ["5A", 0.1, np.inf, "#8F3D3D", "#FFFFFF", 0.8, 0.8],
                ["5B", 0.1, np.inf, "#8F3D3D", "#FFFFFF", 0.8, 0.8],
            ],
            columns=[
                RSDetCol.RISK_SEGMENT,
                RSDetCol.LOWER_RATE,
                RSDetCol.UPPER_RATE,
                RSDetCol.BG_COLOR,
                RSDetCol.FONT_COLOR,
                RSDetCol.MAF_DLR,
                RSDetCol.MAF_ULR,
            ],
        ).rename_axis(index=RSDetCol.ORIG_INDEX.value)
        self.__risk_segment_details.columns = self.__risk_segment_details.columns.map(
            str
        )

        self.__max_iteration_depth = 10
        self.__max_categorical_unique = 20

    @property
    def risk_segment_details(self) -> pd.DataFrame:
        return self.__risk_segment_details.copy()

    @property
    def max_iteration_depth(self) -> int:
        return self.__max_iteration_depth

    @property
    def max_categorical_unique(self) -> int:
        return self.__max_categorical_unique

    @property
    def default_iteation_metadata(self) -> IterationMetadata:
        return IterationMetadata(
            editable=True,
            metric_ids=[MetricID.VOLUME, MetricID.UNT_BAD_RATE, MetricID.DLR_BAD_RATE],
            scalars_enabled=True,
            split_view_enabled=True,
            loss_rate_type=LossRateTypes.DLR,
            initial_filter_ids=[],
            current_filter_ids=[],
            show_prev_iter_details=True,
        )
