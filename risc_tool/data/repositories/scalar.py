from risc_tool.data.models.enums import LossRateTypes, Signature
from risc_tool.data.models.scalar import Scalar
from risc_tool.data.models.types import ChangeIDs
from risc_tool.data.repositories.base import BaseRepository


class ScalarRepository(BaseRepository):
    @property
    def _signature(self) -> Signature:
        return Signature.SCALAR_REPOSITORY

    def __init__(self) -> None:
        super().__init__()

        self.scalars = {
            LossRateTypes.ULR: Scalar(loss_rate_type=LossRateTypes.ULR),
            LossRateTypes.DLR: Scalar(loss_rate_type=LossRateTypes.DLR),
        }

    def on_dependency_update(self, change_ids: ChangeIDs) -> None:
        return

    def get_scalar(self, loss_rate_type: LossRateTypes) -> Scalar:
        return self.scalars[loss_rate_type]

    def get_current_rate(self, loss_rate_type: LossRateTypes):
        return self.get_scalar(loss_rate_type).current_rate

    def set_current_rate(self, loss_rate_type: LossRateTypes, current_rate: float):
        scalar = self.get_scalar(loss_rate_type)
        scalar.current_rate = current_rate

        self.notify_subscribers()

    def get_lifetime_rate(self, loss_rate_type: LossRateTypes):
        return self.get_scalar(loss_rate_type).lifetime_rate

    def set_lifetime_rate(self, loss_rate_type: LossRateTypes, lifetime_rate: float):
        scalar = self.get_scalar(loss_rate_type)
        scalar.lifetime_rate = lifetime_rate

        self.notify_subscribers()


__all__ = ["ScalarRepository"]
