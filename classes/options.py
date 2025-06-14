import typing as t

import numpy as np
import pandas as pd

from classes.constants import DefaultOptions, LossRateTypes, RTDetCol


default_options = DefaultOptions()


class Options:
    def __init__(self):
        self.set_default_values()

    def _recalculate_lower_bounds(self):
        self.risk_tier_details = self.risk_tier_details.reset_index(drop=False)

        for row_i in self.risk_tier_details.index:
            if row_i == 0:
                self.risk_tier_details.loc[row_i, RTDetCol.LOWER_RATE] = 0
                continue

            if (
                self.risk_tier_details.loc[row_i, RTDetCol.UPPER_RATE]
                == self.risk_tier_details.loc[row_i - 1, RTDetCol.UPPER_RATE]
            ):
                self.risk_tier_details.loc[row_i, RTDetCol.LOWER_RATE] = (
                    self.risk_tier_details.loc[row_i - 1, RTDetCol.LOWER_RATE]
                )
                continue

            self.risk_tier_details.loc[row_i, RTDetCol.LOWER_RATE] = (
                self.risk_tier_details.loc[row_i - 1, RTDetCol.UPPER_RATE]
            )

        self.risk_tier_details = self.risk_tier_details.set_index(RTDetCol.ORIG_INDEX)

    def get_color(self, risk_tier: str) -> list[str, str]:
        return (
            self.risk_tier_details.loc[
                (self.risk_tier_details[RTDetCol.RISK_TIER] == risk_tier),
                [RTDetCol.FONT_COLOR, RTDetCol.BG_COLOR],
            ]
            .iloc[0]
            .to_dict()
        )

    def set_default_values(self):
        self.risk_tier_details = default_options.risk_tier_details
        self.max_iteration_depth = default_options.max_iteration_depth

    def add_risk_tier_row(self):
        self.risk_tier_details = pd.concat(
            [
                self.risk_tier_details,
                pd.DataFrame(
                    {
                        RTDetCol.RISK_TIER: "",
                        RTDetCol.LOWER_RATE: -np.inf,
                        RTDetCol.UPPER_RATE: np.inf,
                        RTDetCol.BG_COLOR: "#000000",
                        RTDetCol.FONT_COLOR: "#FFFFFF",
                        RTDetCol.MAF_DLR: 1.0,
                        RTDetCol.MAF_ULR: 1.0,
                    },
                    index=[self.risk_tier_details.index.max() + 1],
                ),
            ],
            ignore_index=False,
        ).rename_axis(index=RTDetCol.ORIG_INDEX)

        self._recalculate_lower_bounds()

    def delete_selected_risk_tier_rows(self, row_indices):
        self.risk_tier_details = self.risk_tier_details.drop(row_indices)

        self._recalculate_lower_bounds()

    def set_risk_tier_name(self, row_index: int, name: str):
        self.risk_tier_details.loc[row_index, RTDetCol.RISK_TIER] = name

        self._recalculate_lower_bounds()

    def set_risk_tier_upper_rate(self, new_upper_rates: pd.Series):
        self.risk_tier_details.loc[new_upper_rates.index, RTDetCol.UPPER_RATE] = (
            new_upper_rates
        )

        self.risk_tier_details = self.risk_tier_details.sort_values([
            RTDetCol.UPPER_RATE,
            RTDetCol.RISK_TIER,
        ])

        self._recalculate_lower_bounds()

    def set_risk_tier_font_color(self, row_indices: t.Iterator[int], color: str):
        self.risk_tier_details.loc[row_indices, RTDetCol.FONT_COLOR] = color.upper()

    def set_risk_tier_bg_color(self, row_indices: t.Iterator[int], color: str):
        self.risk_tier_details.loc[row_indices, RTDetCol.BG_COLOR] = color.upper()

    def set_risk_tier_maf(
        self, row_index: int, maf: float, loss_rate_type: LossRateTypes
    ):
        column_name = (
            RTDetCol.MAF_DLR
            if loss_rate_type == LossRateTypes.DLR
            else RTDetCol.MAF_ULR
        )
        self.risk_tier_details.loc[row_index, column_name] = maf


__all__ = ["Options"]
