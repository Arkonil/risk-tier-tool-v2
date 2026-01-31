import pandas as pd

from risc_tool.data.models.changes import ChangeTracker
from risc_tool.data.models.enums import DataExplorerTabName, Signature, VariableType
from risc_tool.data.models.types import ChangeIDs, DataSourceID, FilterID
from risc_tool.data.repositories.data import DataRepository
from risc_tool.data.repositories.filter import FilterRepository
from risc_tool.data.services.iv_calculation import calculate_iv
from risc_tool.utils.hash_boolean_series import hash_boolean_series


class DataExplorerViewModel(ChangeTracker):
    @property
    def _signature(self) -> Signature:
        return Signature.DATA_EXPLORER_VIEW_MODEL

    def __init__(
        self, data_repository: DataRepository, filter_repository: FilterRepository
    ) -> None:
        super().__init__(dependencies=[data_repository, filter_repository])

        # Dependencies
        self.data_repository = data_repository
        self.filter_repository = filter_repository

        # Tab navigation
        self.tab_names: list[DataExplorerTabName] = [DataExplorerTabName.IV_ANALYSIS]
        self.current_tab_name = self.tab_names[0]

        # IV
        self.__iv_data_sources: list[DataSourceID] = []
        self.iv_current_target: str | None = None
        self.iv_current_variables: list[str] = []
        self.iv_current_filter_ids: list[FilterID] = []
        self.__iv_cache: pd.DataFrame = self.__empty_iv_cache
        self.iv_errors: list[Exception] = []
        self.iv_warnings: list[str] = []

    @property
    def __empty_iv_cache(self):
        return (
            pd.DataFrame(columns=["target", "input", "filter_hash", "iv"])
            .astype({
                "target": pd.StringDtype(),
                "input": pd.StringDtype(),
                "filter_hash": pd.StringDtype(),
                "iv": pd.Float64Dtype(),
            })
            .set_index(["target", "input", "filter_hash"])
        )

    def _update_iv_inputs(self):
        self.__iv_data_sources = list(
            set(self.iv_data_sources) & set(self.data_repository.data_sources)
        )

        if self.iv_current_target not in self.available_target_columns:
            self.iv_current_target = None

        self.iv_current_variables = list(
            set(self.iv_current_variables) & set(self.available_input_columns)
        )
        self.iv_current_filter_ids = list(
            set(self.iv_current_filter_ids) & set(self.filter_repository.filters.keys())
        )

        self.__iv_cache: pd.DataFrame = self.__empty_iv_cache

        self.iv_errors.clear()
        self.iv_warnings.clear()

    def on_dependency_update(self, change_ids: ChangeIDs):
        # Updating IV input variables and cache
        self._update_iv_inputs()

    # Common
    @property
    def all_data_source_ids(self) -> list[DataSourceID]:
        return [ds_id for ds_id in self.data_repository.data_sources]

    def get_data_source_label(self, data_source_id: DataSourceID):
        return self.data_repository.data_sources[data_source_id].label

    @property
    def sample_loaded(self) -> bool:
        return self.data_repository.sample_loaded

    @property
    def common_columns(self) -> list[str]:
        return self.data_repository.common_columns

    @property
    def all_filters(self):
        return self.filter_repository.get_filters()

    # IV
    @property
    def iv_data_sources(self):
        return self.__iv_data_sources

    @iv_data_sources.setter
    def iv_data_sources(self, value: list[DataSourceID]):
        self.__iv_data_sources = value

        self._update_iv_inputs()

    @property
    def available_target_columns(self) -> list[str]:
        if not self.data_repository.sample_loaded:
            return []

        return [
            col
            for col, col_type in self.data_repository.available_columns(
                self.iv_data_sources
            )
            if col_type == VariableType.NUMERICAL
        ]

    @property
    def available_input_columns(self) -> list[str]:
        if not self.data_repository.sample_loaded:
            return []

        return [
            col
            for col, _ in self.data_repository.available_columns(self.iv_data_sources)
        ]

    def get_iv_df(
        self,
        target_variable: str | None,
        input_variables: list[str],
        filter_ids: list[FilterID],
    ) -> pd.DataFrame | None:
        self.iv_errors.clear()
        self.iv_warnings.clear()

        if target_variable is None or not input_variables:
            self.iv_warnings.append(
                "Please select a target variable and at least one input variable to calculate IV."
            )
            return None

        if not self.data_repository.sample_loaded:
            self.iv_errors.append(
                ValueError("Sample data not loaded. Please import data first.")
            )
            return None

        available_columns = self.data_repository.available_columns(self.iv_data_sources)

        if (target_variable, VariableType.NUMERICAL) not in available_columns:
            self.iv_errors.append(
                ValueError(
                    f"Target variable `{target_variable}` is not found in the selected data sources or is not numerical."
                )
            )
            return None

        input_cols_available: list[str] = []

        for input_col in input_variables:
            if ((input_col, VariableType.CATEGORICAL) not in available_columns) and (
                (input_col, VariableType.NUMERICAL) not in available_columns
            ):
                self.iv_errors.append(
                    ValueError(
                        f"Variable `{input_col}` is not found in the selected data sources."
                    )
                )
            else:
                input_cols_available.append(input_col)

        if not input_cols_available:
            self.iv_errors.append(
                ValueError(
                    "Please select at least one valid input variable to calculate IV."
                )
            )
            return None

        filter_ids_available: list[FilterID] = []

        for filter_id in filter_ids:
            if filter_id not in self.filter_repository.filters:
                self.iv_errors.append(ValueError(f"Filter `{filter_id}` is not found."))
            else:
                filter_ids_available.append(filter_id)

        mask = self.filter_repository.get_mask(filter_ids=filter_ids_available)
        mask_hash = hash_boolean_series(mask)

        iv_df = pd.DataFrame(columns=["variable", "iv"])
        target: pd.Series | None = None

        for input_col in input_cols_available:
            try:
                cached_iv = self.__iv_cache.loc[
                    (target_variable, input_col, mask_hash), "iv"
                ]

                if pd.isna(cached_iv) or not isinstance(cached_iv, float):
                    raise ValueError(
                        f"Expected float while calculating IV of {input_col}, but got {type(cached_iv)}"
                    )

                iv_df.loc[len(iv_df)] = [input_col, cached_iv]

            except KeyError:
                if target is None:
                    target = self.data_repository.load_column(target_variable)

                target_m = target[mask]
                target_m = target_m.loc[(list(self.iv_data_sources),)]

                if not target_m.isin([0, 1]).all():
                    values = list(set(target_m.drop_duplicates().to_list()) - {0, 1})
                    if len(values) > 10:
                        values_str = ", ".join(
                            map(str, values[:9] + ["..."] + values[-1:])
                        )
                    else:
                        values_str = ", ".join(map(str, values))

                    self.iv_errors.append(
                        ValueError(
                            f"Target variable must be binary (0 or 1).\n\n"
                            f"Following values were found: [{values_str}]"
                        )
                    )

                    return None

                variable = self.data_repository.load_column(input_col)
                variable_m = variable[mask]
                variable_m = variable_m.loc[(list(self.iv_data_sources),)]

                if (
                    not pd.api.types.is_numeric_dtype(variable_m)
                    and variable_m.nunique() > 10
                ):
                    self.iv_warnings.append(
                        f"Variable `{input_col}` is not numerical and has more than 10 unique values. "
                        f"Total unique values: {variable_m.nunique()}"
                    )
                    continue

                iv = calculate_iv(variable_m, target_m)

                self.__iv_cache.loc[(target_variable, input_col, mask_hash)] = iv

                iv_df.loc[len(iv_df)] = [input_col, iv]

            except Exception as error:
                self.iv_errors.append(error)

        if iv_df.empty:
            return None

        iv_df.sort_values("iv", ascending=False, inplace=True)

        return iv_df
