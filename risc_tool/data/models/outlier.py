import pandas as pd

from risc_tool.data.models.enums import ComparisonOperation, PercentileOptions
from risc_tool.data.models.filter import Filter
from risc_tool.data.models.json_models import FilterJSON
from risc_tool.data.models.types import FilterID


class OutlierRule(Filter):
    def __init__(
        self,
        uid: FilterID,
        variable: pd.Series,
        comparison_op: ComparisonOperation,
        comparison_base: PercentileOptions | float,
    ):
        super().__init__(uid, "", "")

        self.variable = variable.copy()
        self.variable_name: str = str(variable.name)
        self.comparison_op: ComparisonOperation = comparison_op
        self.comparison_base: PercentileOptions | float = comparison_base

        mode = variable.mode().iloc[0]

        if isinstance(self.comparison_base, PercentileOptions):
            variable_m = variable.loc[variable != mode]

            match comparison_base:
                case PercentileOptions.PERC_1:
                    comparison_base = variable_m.quantile(0.01, interpolation="linear")
                case PercentileOptions.PERC_5:
                    comparison_base = variable_m.quantile(0.05, interpolation="linear")
                case PercentileOptions.PERC_10:
                    comparison_base = variable_m.quantile(0.10, interpolation="linear")
                case PercentileOptions.PERC_25:
                    comparison_base = variable_m.quantile(0.25, interpolation="linear")
                case PercentileOptions.PERC_50:
                    comparison_base = variable_m.quantile(0.50, interpolation="linear")
                case PercentileOptions.PERC_75:
                    comparison_base = variable_m.quantile(0.75, interpolation="linear")
                case PercentileOptions.PERC_90:
                    comparison_base = variable_m.quantile(0.90, interpolation="linear")
                case PercentileOptions.PERC_95:
                    comparison_base = variable_m.quantile(0.95, interpolation="linear")
                case PercentileOptions.PERC_99:
                    comparison_base = variable_m.quantile(0.99, interpolation="linear")

            self.name = f"{self.variable_name} {self.comparison_op.value} {PercentileOptions.format_perc(self.comparison_base.value)}"
        else:
            self.name = f"{self.variable_name} {self.comparison_op.value} {self.comparison_base}"

        self.query = f"~((`{self.variable_name}` {comparison_op} {comparison_base}) & (`{self.variable_name}` != {mode}))"

    def to_dict(self) -> FilterJSON:
        return FilterJSON(
            uid=self.uid,
            name=self.name,
            query=self.query,
            used_columns=self.used_columns,
            variable_name=self.variable_name,
            comparison_op=self.comparison_op,
            comparison_base=self.comparison_base,
            is_outlier=True,
        )

    @classmethod
    def from_dict(
        cls, data: FilterJSON, variable: pd.Series | None = None
    ) -> "OutlierRule":
        if variable is None:
            raise ValueError("Variable must be provided.")

        instance = cls(
            uid=data.uid,
            variable=variable,
            comparison_op=data.comparison_op,
            comparison_base=data.comparison_base,
        )

        return instance

    def duplicate(self, uid: FilterID | None = None, name: str | None = None):
        if uid is None:
            uid = self.uid
        if name is None:
            name = self.name

        new_instance = OutlierRule(
            uid=uid,
            variable=self.variable,
            comparison_op=self.comparison_op,
            comparison_base=self.comparison_base,
        )

        new_instance.used_columns = self.used_columns.copy()
        new_instance.mask = self.mask.copy() if self.mask is not None else None

        return new_instance


__all__ = ["OutlierRule"]
