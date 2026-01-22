from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from risc_tool.data.models.data_source import DataSource
from risc_tool.data.models.enums import VariableType
from risc_tool.data.models.types import DataSourceID


@pytest.fixture
def data_dir():
    # Assuming the test is running from project root or we can find it relative to this file
    # This file is in risc_tool/tests/
    # data dir is in p:\python\risk-tier-tool\data\
    # So it is ../../data relative to this file
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    return base_dir / "data"


@pytest.fixture
def real_csv_path(data_dir):
    p = data_dir / "test_data.csv"
    if not p.exists():
        pytest.skip(f"Test data file not found: {p}")
    return p


@pytest.fixture
def real_excel_path(data_dir):
    p = data_dir / "test_data.xlsx"
    if not p.exists():
        pytest.skip(f"Test data file not found: {p}")
    return p


@pytest.fixture
def valid_datasource_data(real_csv_path):
    return {
        "uid": DataSourceID(1),
        "label": "Test Source CSV",
        "filepath": str(real_csv_path),
        "read_mode": "CSV",
        "delimiter": ",",
        "sheet_name": "0",
        "header_row": 0,
        "sample_row_count": 5,
    }


@pytest.fixture
def valid_excel_datasource_data(real_excel_path):
    return {
        "uid": DataSourceID(2),
        "label": "Test Source Excel",
        "filepath": str(real_excel_path),
        "read_mode": "EXCEL",
        "delimiter": ",",  # Delimiter ignored for Excel usually, but field exists
        "sheet_name": "0",  # Pandas reads first sheet by default if "0"? Or we might need actual sheet name or 0 index behavior check
        "header_row": 0,
        "sample_row_count": 5,
    }


class TestDataSourceSerialization:
    def test_to_dict(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        data = ds.to_dict()
        assert data["uid"] == valid_datasource_data["uid"]
        assert data["label"] == valid_datasource_data["label"]
        assert data["filepath"] == valid_datasource_data["filepath"]

    def test_from_dict(self, valid_datasource_data):
        ds = DataSource.from_dict(valid_datasource_data)
        assert isinstance(ds, DataSource)
        assert ds.uid == valid_datasource_data["uid"]
        assert str(ds.filepath) == valid_datasource_data["filepath"]

    def test_from_dict_invalid_type(self):
        with pytest.raises(TypeError, match="The input must be a dictionary"):
            DataSource.from_dict("not a dict")

    def test_from_dict_sentinels(self, valid_datasource_data):
        # Test TEMPORARY sentinel
        data = valid_datasource_data.copy()
        data["uid"] = DataSourceID.TEMPORARY
        ds = DataSource.from_dict(data)
        assert ds.uid is DataSourceID.TEMPORARY

        # Test EMPTY sentinel
        data = valid_datasource_data.copy()
        data["uid"] = DataSourceID.EMPTY
        ds = DataSource.from_dict(data)
        assert ds.uid is DataSourceID.EMPTY


class TestDataSourceConfig:
    def test_validate_read_config_valid_csv(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        # Should not raise
        ds.validate_read_config()

    def test_validate_read_config_valid_excel(self, valid_excel_datasource_data):
        ds = DataSource(**valid_excel_datasource_data)
        # Should not raise
        ds.validate_read_config()

    def test_validate_read_config_file_not_found(self, valid_datasource_data):
        data = valid_datasource_data.copy()
        data["filepath"] = "non_existent_file.csv"
        # We need to bypass validation at creation if possible or just use a path that 'stat' says is valid but doesn't exist?
        # Actually Pydantic FilePath will validate existence at init.
        # So we can't easily test 'validate_read_config' failing for FileNotFoundError unless we trick Pydantic or delete file after init.

        # Create a temp file then delete it
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            path = tmp.name

        data["filepath"] = path
        ds = DataSource(**data)
        os.remove(path)

        with pytest.raises(FileNotFoundError):
            ds.validate_read_config()

    def test_validate_read_config_invalid_extension(
        self, tmp_path, valid_datasource_data
    ):
        p = tmp_path / "test.txt"
        p.write_text("content")

        data = valid_datasource_data.copy()
        data["filepath"] = str(p)
        data["read_mode"] = "CSV"

        ds = DataSource(**data)
        with pytest.raises(ValueError, match="Selected file is not a CSV"):
            ds.validate_read_config()

    def test_validate_read_config_excel_extension(
        self, tmp_path, valid_datasource_data
    ):
        p = tmp_path / "test_wrong.txt"
        p.write_text("content")

        data = valid_datasource_data.copy()
        data["filepath"] = str(p)
        data["read_mode"] = "EXCEL"

        ds = DataSource(**data)
        with pytest.raises(ValueError, match="Selected file is not a EXCEL"):
            ds.validate_read_config()


class TestDataSourceLoading:
    def test_load_sample_csv(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        ds.load_sample()

        assert ds.sample_loaded is True
        assert ds._sample_df is not None
        assert not ds._sample_df.empty
        # Check some known columns from inspection
        assert "credit_score" in ds._sample_df.columns
        assert "income" in ds._sample_df.columns
        # Check size - we know file is ~80k lines
        assert ds.df_size > 70000

    def test_load_sample_excel(self, valid_excel_datasource_data):
        ds = DataSource(**valid_excel_datasource_data)
        ds.load_sample()

        assert ds.sample_loaded is True
        assert ds._sample_df is not None
        assert not ds._sample_df.empty
        # Assuming Excel has similar structure/columns as CSV for this test data
        # If not, checks might need adjustment, but usually test_data.* are copies
        assert "credit_score" in ds._sample_df.columns

    def test_load_data(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        # We need to set df_size or call load_sample first?
        # load_data doesn't depend on load_sample but usually used after.
        # But we can call it directly.

        columns = ["credit_score", "employment_status"]
        df = ds.load_data(columns)

        assert list(df.columns) == columns
        assert not df.empty
        assert len(df) > 70000

    def test_column_types(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        ds.load_sample()

        types = ds.column_types
        # Convert to dictionary for easier lookup
        type_dict = {name: c_type for name, c_type in types}

        assert "credit_score" in type_dict
        # Expect numerical
        assert type_dict["credit_score"] == VariableType.NUMERICAL

        assert "employment_status" in type_dict
        # Expect categorical (strings)
        assert type_dict["employment_status"] == VariableType.CATEGORICAL

    def test_index(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)

        # Test when not loaded
        with pytest.raises(ValueError, match="Data not loaded"):
            _ = ds.index

        # Test with df_size
        ds.df_size = 5
        idx = ds.index
        assert isinstance(idx, pd.RangeIndex)
        assert len(idx) == 5

        # Test with loaded _df
        ds._df = pd.DataFrame({"col": [1, 2, 3]}, index=[10, 11, 12])
        idx = ds.index
        assert list(idx) == [10, 11, 12]


class TestDataSourceColumnOperations:
    @pytest.fixture
    def loaded_ds(self, valid_datasource_data):
        ds = DataSource(**valid_datasource_data)
        ds._sample_df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
        ds.df_size = 2

        # Pre-populate _df to simulate cache
        ds._df = pd.DataFrame()
        # "A (Numerical)"
        ds._df["A (Numerical)"] = pd.Series([1, 2])
        return ds

    def test_load_column_from_cache_hit(self, loaded_ds):
        col = loaded_ds._load_column_from_cache("A", VariableType.NUMERICAL)
        assert col.tolist() == [1, 2]

    def test_load_column_from_cache_miss(self, loaded_ds):
        with pytest.raises(IndexError):
            loaded_ds._load_column_from_cache("Z", VariableType.NUMERICAL)

    def test_load_column_from_cache_alternative_type(self, loaded_ds):
        # Setup: cached as Numerical, request as Categorical if possible?
        # The code logic:
        # if req=Cat and alt=Num exists? -> No, check code:
        # if req=Cat and alt=Cat exists? No, alt is OTHER type.
        # if req=Cat, alt=Num.

        # Let's add "B (Categorical)" to cache
        loaded_ds._df["B (Categorical)"] = pd.Series(["x", "y"], dtype="category")

        # Request B as Numerical -> Logic check
        # if req=Num and alt=Cat exists?
        # try pd.to_numeric

        # Case 1: Can convert
        loaded_ds._df["C (Categorical)"] = pd.Series(["10", "20"], dtype="category")
        col = loaded_ds._load_column_from_cache("C", VariableType.NUMERICAL)
        assert col.dtype.kind in "iu" or col.dtype.kind == "f"  # integer or float
        assert col.tolist() == [10, 20]
        # Should be cached now
        assert "C (Numerical)" in loaded_ds._df.columns

        # Case 2: Cannot convert
        col_b = loaded_ds._load_column_from_cache("B", VariableType.NUMERICAL)
        # Exception caught, returns copy of alternative
        assert col_b.tolist() == ["x", "y"]
        # Should NOT be cached as Numerical because it failed?
        # Code: return self._df[alternative_column_name].copy()

    @patch("risc_tool.data.models.data_source.DataSource.load_data")
    def test_load_columns_full_flow(self, mock_load_data, loaded_ds):
        # We have A (Numerical) in cache.
        # We ask for:
        # 1. A (Numerical) -> Cache hit
        # 2. B (Categorical) -> Not in cache, but available in sample -> Load
        # 3. C (Numerical) -> Not in sample -> Generate empty/NaN?

        # Setup mock for load_data
        # It calls load_data with available columns. Here ["B"]
        mock_load_data.return_value = pd.DataFrame(
            {"B": ["x", "y"]}, index=loaded_ds.index
        )

        # Prepare "C" which is missing - expected behavior from code:
        # "new_generated_columns" created with index.

        result_df = loaded_ds.load_columns(
            column_names=["A", "B", "C"],
            column_types=[
                VariableType.NUMERICAL,
                VariableType.CATEGORICAL,
                VariableType.NUMERICAL,
            ],
        )

        # Check result columns
        # Code renames columns back to original names using regex pattern match if they match "Name (Type)"
        # Wait, the rename logic:
        # final_df has "A (Numerical)", "B (Categorical)", etc.
        # rename_col strips the type suffix.

        assert "A" in result_df.columns
        assert "B" in result_df.columns
        assert "C" in result_df.columns

        assert result_df["A"].tolist() == [1, 2]
        assert result_df["B"].tolist() == ["x", "y"]
        # C was generated empty?
        assert result_df["C"].isna().all()

        # Verify internal _df cache updated
        assert "B (Categorical)" in loaded_ds._df.columns
        assert "C (Numerical)" in loaded_ds._df.columns
