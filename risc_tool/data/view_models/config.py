import pandas as pd

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import LossRateTypes, Signature
from risc_tool.data.models.types import ChangeIDs
from risc_tool.data.repositories.metric import MetricRepository
from risc_tool.data.repositories.options import OptionRepository
from risc_tool.data.repositories.scalar import ScalarRepository


class ConfigViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.CONFIG_VIEW_MODEL

    def __init__(
        self,
        options_repository: OptionRepository,
        scalar_repository: ScalarRepository,
        metric_repository: MetricRepository,
    ):
        super().__init__(
            dependencies=[options_repository, scalar_repository, metric_repository]
        )

        self.__options_repository = options_repository
        self.__scalar_repository = scalar_repository
        self.__metric_repository = metric_repository

    def on_dependency_update(self, change_ids: ChangeIDs):
        pass

    # Risk Segment Details
    @property
    def risk_segment_details(self):
        return self.__options_repository.risk_segment_details

    def add_risk_seg_row(self):
        return self.__options_repository.add_risk_seg_row()

    def delete_selected_risk_seg_rows(self, row_indices: pd.Index):
        return self.__options_repository.delete_selected_risk_seg_rows(row_indices)

    def set_risk_seg_font_color(self, row_indices: list[int], color: str):
        return self.__options_repository.set_risk_seg_font_color(row_indices, color)

    def set_risk_seg_bg_color(self, row_indices: list[int], color: str):
        return self.__options_repository.set_risk_seg_bg_color(row_indices, color)

    def set_risk_seg_default_values(self):
        return self.__options_repository.set_risk_seg_default_values()

    def set_risk_seg_name(self, row_index: int, name: str):
        return self.__options_repository.set_risk_seg_name(row_index, name)

    def set_risk_seg_upper_rate(self, new_upper_rates):
        return self.__options_repository.set_risk_seg_upper_rate(new_upper_rates)

    # Scalars
    @property
    def current_rate_mob(self):
        return self.__metric_repository.current_rate_mob

    @property
    def lifetime_rate_mob(self):
        return self.__metric_repository.lifetime_rate_mob

    def get_scalar(self, loss_rate_type: LossRateTypes):
        return self.__scalar_repository.get_scalar(loss_rate_type)

    def get_current_rate(self, loss_rate_type: LossRateTypes):
        return self.__scalar_repository.get_current_rate(loss_rate_type)

    def get_lifetime_rate(self, loss_rate_type: LossRateTypes):
        return self.__scalar_repository.get_lifetime_rate(loss_rate_type)

    def set_current_rate(self, loss_rate_type: LossRateTypes, new_rate: float):
        return self.__scalar_repository.set_current_rate(loss_rate_type, new_rate)

    def set_lifetime_rate(self, loss_rate_type: LossRateTypes, new_rate: float):
        return self.__scalar_repository.set_lifetime_rate(loss_rate_type, new_rate)

    def get_color(self, risk_seg_name: str):
        return self.__options_repository.get_color(risk_seg_name)

    def set_risk_seg_maf(
        self, row_index: int, maf: float, loss_rate_type: LossRateTypes
    ):
        return self.__options_repository.set_risk_seg_maf(
            row_index=row_index, maf=maf, loss_rate_type=loss_rate_type
        )


__all__ = ["ConfigViewModel"]
