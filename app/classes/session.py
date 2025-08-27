import io
import json
import re
import zipfile

import numpy as np
import pandas as pd

from classes.data import Data
from classes.filter_container import FilterContainer
from classes.metric_container import MetricContainer
from classes.summary_page_state import SummaryPageState
from classes.scalars import Scalar
from classes.iteration_graph import IterationGraph
from classes.options import Options
from classes.constants import LossRateTypes, README_CONTENT, VariableType


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, set):
            return list(obj)
        return super(NpEncoder, self).default(obj)


class Session:
    def __init__(self):
        super().__init__()

        self.data = Data()

        self.reset()

    def reset(self):
        self.data.reset()
        self.dlr_scalars = Scalar(LossRateTypes.DLR)
        self.ulr_scalars = Scalar(LossRateTypes.ULR)
        self.iteration_graph = IterationGraph()
        self.summary_page_state = SummaryPageState()
        self.options = Options()
        self.filter_container = FilterContainer()
        self.metric_container = MetricContainer()

    def to_rt_zip_buffer(self) -> io.BytesIO:
        data_json = self.data.to_dict()
        dlr_scalars_json = self.dlr_scalars.to_dict()
        ulr_scalars_json = self.ulr_scalars.to_dict()
        iteration_graph_json = self.iteration_graph.to_dict()
        summary_page_state_json = self.summary_page_state.to_dict()
        options_json = self.options.to_dict()
        fc_json = self.filter_container.to_dict()
        mc_json = self.metric_container.to_dict()

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("data.json", json.dumps(data_json, indent=4, cls=NpEncoder))
            zipf.writestr(
                "dlr_scalars.json",
                json.dumps(dlr_scalars_json, indent=4, cls=NpEncoder),
            )
            zipf.writestr(
                "ulr_scalars.json",
                json.dumps(ulr_scalars_json, indent=4, cls=NpEncoder),
            )
            zipf.writestr(
                "iteration_graph.json",
                json.dumps(iteration_graph_json, indent=4, cls=NpEncoder),
            )
            zipf.writestr(
                "summary_page_state.json",
                json.dumps(summary_page_state_json, indent=4, cls=NpEncoder),
            )
            zipf.writestr(
                "options.json", json.dumps(options_json, indent=4, cls=NpEncoder)
            )
            zipf.writestr(
                "filter_container.json", json.dumps(fc_json, indent=4, cls=NpEncoder)
            )
            zipf.writestr(
                "metric_container.json", json.dumps(mc_json, indent=4, cls=NpEncoder)
            )
            zipf.writestr("README.md", README_CONTENT.strip())

            # Convert DataFrame to Parquet and write to zip
            if self.data.df is not None and not self.data.df.empty:
                df_parquet_buffer = io.BytesIO()
                self.data.df.to_parquet(df_parquet_buffer)
                df_parquet_buffer.seek(0)

                zipf.writestr("df.parquet", df_parquet_buffer.getvalue())

            # Convert sample_df to Parquet and write to zip
            if self.data.sample_df is not None and not self.data.sample_df.empty:
                sample_df_parquet_buffer = io.BytesIO()
                self.data.sample_df.to_parquet(sample_df_parquet_buffer)
                sample_df_parquet_buffer.seek(0)

                zipf.writestr("sample_df.parquet", sample_df_parquet_buffer.getvalue())

        zip_buffer.seek(0)

        return zip_buffer

    def import_rt_zip(self, zip_buffer: io.BytesIO):
        with zipfile.ZipFile(zip_buffer, "r") as zipf:
            data_exists = (
                "df.parquet" in zipf.namelist()
                and "sample_df.parquet" in zipf.namelist()
                and "data.json" in zipf.namelist()
            )
            graph_exists = "iteration_graph.json" in zipf.namelist()
            filter_exists = "filter_container.json" in zipf.namelist()
            metric_exists = "metric_container.json" in zipf.namelist()

            if data_exists:
                # Read df from Parquet if it exists
                df_parquet_buffer = io.BytesIO(zipf.read("df.parquet"))
                df = pd.read_parquet(df_parquet_buffer)
                df = df.convert_dtypes()

                for col in df.columns:
                    if re.match(rf".+ \({VariableType.CATEGORICAL}\)$", col):
                        df[col] = df[col].astype("category")

                # Read sample_df from Parquet if it exists
                sample_df_parquet_buffer = io.BytesIO(zipf.read("sample_df.parquet"))
                sample_df = pd.read_parquet(sample_df_parquet_buffer)

                data_json = json.loads(zipf.read("data.json"))

                data = Data.from_dict(data_json)
                data.df = df
                data.sample_df = sample_df

            else:
                data = Data()

            if data_exists and graph_exists:
                iteration_graph_json = json.loads(zipf.read("iteration_graph.json"))
                iteration_graph = IterationGraph.from_dict(iteration_graph_json, data)
            else:
                iteration_graph = IterationGraph()

            if data_exists and graph_exists:
                variables = list(
                    map(
                        lambda iteration: iteration.variable.name,
                        iteration_graph.iterations.values(),
                    )
                )
                if not all(variable in data.df.columns for variable in variables):
                    raise ValueError(
                        "The variables in the iteration graph do not match the columns in the data."
                    )

            if data_exists and filter_exists:
                filter_container_json = json.loads(zipf.read("filter_container.json"))
                filter_container = FilterContainer.from_dict(
                    filter_container_json, data
                )
            else:
                filter_container = FilterContainer()

            if data_exists and metric_exists:
                metric_container_json = json.loads(zipf.read("metric_container.json"))
                metric_container = MetricContainer.from_dict(metric_container_json)
            else:
                metric_container = MetricContainer()

            if "dlr_scalars.json" in zipf.namelist():
                dlr_scalars_json = json.loads(zipf.read("dlr_scalars.json"))
                dlr_scalars = Scalar.from_dict(dlr_scalars_json)
            else:
                dlr_scalars = Scalar(LossRateTypes.DLR)

            if "ulr_scalars.json" in zipf.namelist():
                ulr_scalars_json = json.loads(zipf.read("ulr_scalars.json"))
                ulr_scalars = Scalar.from_dict(ulr_scalars_json)
            else:
                ulr_scalars = Scalar(LossRateTypes.ULR)

            if "summary_page_state.json" in zipf.namelist():
                summary_page_state_json = json.loads(
                    zipf.read("summary_page_state.json")
                )
                summary_page_state = SummaryPageState.from_dict(summary_page_state_json)
            else:
                summary_page_state = SummaryPageState()

            if "options.json" in zipf.namelist():
                options_json = json.loads(zipf.read("options.json"))
                options = Options.from_dict(options_json)
            else:
                options = Options()

            self.reset()

            self.data = data
            self.dlr_scalars = dlr_scalars
            self.ulr_scalars = ulr_scalars
            self.iteration_graph = iteration_graph
            self.summary_page_state = summary_page_state
            self.options = options
            self.filter_container = filter_container
            self.metric_container = metric_container
