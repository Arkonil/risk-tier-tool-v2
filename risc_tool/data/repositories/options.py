import numpy as np
import pandas as pd

from risc_tool.data.models.defaults import DefaultOptions
from risc_tool.data.models.enums import LossRateTypes, RSDetCol, Signature
from risc_tool.data.models.types import ChangeIDs
from risc_tool.data.repositories.base import BaseRepository

default_options = DefaultOptions()


class OptionRepository(BaseRepository):
    @property
    def _signature(self) -> Signature:
        return Signature.OPTION_REPOSITORY

    def __init__(self):
        super().__init__()

        self.risk_segment_details = default_options.risk_segment_details
        self.max_iteration_depth = default_options.max_iteration_depth
        self.max_categorical_unique = default_options.max_categorical_unique

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        return

    def __recalculate_lower_bounds(self):
        self.risk_segment_details = self.risk_segment_details.reset_index(drop=False)

        for row_i in self.risk_segment_details.index:
            if row_i == 0:
                self.risk_segment_details.loc[row_i, RSDetCol.LOWER_RATE] = 0
                continue

            if (
                self.risk_segment_details.loc[row_i, RSDetCol.UPPER_RATE]
                == self.risk_segment_details.loc[row_i - 1, RSDetCol.UPPER_RATE]
            ):
                self.risk_segment_details.loc[row_i, RSDetCol.LOWER_RATE] = (
                    self.risk_segment_details.loc[row_i - 1, RSDetCol.LOWER_RATE]
                )
                continue

            self.risk_segment_details.loc[row_i, RSDetCol.LOWER_RATE] = (
                self.risk_segment_details.loc[row_i - 1, RSDetCol.UPPER_RATE]
            )

        self.risk_segment_details = self.risk_segment_details.set_index(
            RSDetCol.ORIG_INDEX
        )

    def get_color(self, risk_seg_name: str):
        return self.risk_segment_details.loc[
            (self.risk_segment_details[RSDetCol.RISK_SEGMENT] == risk_seg_name),
            [RSDetCol.FONT_COLOR, RSDetCol.BG_COLOR],
        ]

    def add_risk_seg_row(self):
        self.risk_segment_details = pd.concat(
            [
                self.risk_segment_details,
                pd.DataFrame(
                    {
                        RSDetCol.RISK_SEGMENT.value: "",
                        RSDetCol.LOWER_RATE.value: -np.inf,
                        RSDetCol.UPPER_RATE.value: np.inf,
                        RSDetCol.BG_COLOR.value: "#000000",
                        RSDetCol.FONT_COLOR.value: "#FFFFFF",
                        RSDetCol.MAF_DLR.value: 1.0,
                        RSDetCol.MAF_ULR.value: 1.0,
                    },
                    index=[self.risk_segment_details.index.max() + 1],
                ),
            ],
            ignore_index=False,
        ).rename_axis(index=RSDetCol.ORIG_INDEX.value)

        self.__recalculate_lower_bounds()

        self.notify_subscribers()

    def delete_selected_risk_seg_rows(self, row_indices: pd.Index):
        self.risk_segment_details = self.risk_segment_details.drop(row_indices)

        self.__recalculate_lower_bounds()

        self.notify_subscribers()

    def set_risk_seg_name(self, row_index: int, name: str):
        self.risk_segment_details.loc[row_index, RSDetCol.RISK_SEGMENT] = name

        self.__recalculate_lower_bounds()

        self.notify_subscribers()

    def set_risk_seg_upper_rate(self, new_upper_rates: pd.Series):
        self.risk_segment_details.loc[new_upper_rates.index, RSDetCol.UPPER_RATE] = (
            new_upper_rates
        )

        self.risk_segment_details = self.risk_segment_details.sort_values([
            RSDetCol.UPPER_RATE,
            RSDetCol.RISK_SEGMENT,
        ])

        self.__recalculate_lower_bounds()

        self.notify_subscribers()

    def set_risk_seg_font_color(self, row_indices: list[int], color: str):
        self.risk_segment_details.loc[row_indices, RSDetCol.FONT_COLOR] = color.upper()

        self.notify_subscribers()

    def set_risk_seg_bg_color(self, row_indices: list[int], color: str):
        self.risk_segment_details.loc[row_indices, RSDetCol.BG_COLOR] = color.upper()

        self.notify_subscribers()

    def set_risk_seg_maf(
        self, row_index: int, maf: float, loss_rate_type: LossRateTypes
    ):
        column_name = (
            RSDetCol.MAF_DLR
            if loss_rate_type == LossRateTypes.DLR
            else RSDetCol.MAF_ULR
        )
        self.risk_segment_details.loc[row_index, column_name] = maf

        self.notify_subscribers()

    def set_risk_seg_default_values(self):
        self.risk_segment_details = default_options.risk_segment_details

        self.notify_subscribers()
