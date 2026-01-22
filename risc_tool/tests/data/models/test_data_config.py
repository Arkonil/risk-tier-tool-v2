from risc_tool.data.models.data_config import DataConfig


def test_data_config_create_completion():
    c = DataConfig.create_completion("simple_col")
    assert c.value == "simple_col"

    c_space = DataConfig.create_completion("col with spaces")
    assert c_space.value == "`col with spaces`"


def test_data_config_refresh_and_get():
    dc = DataConfig()
    all_cols = ["A", "B", "C"]
    common_cols = ["A"]

    dc.refresh(common_columns=common_cols, all_columns=all_cols)

    assert dc.all_columns == all_cols
    assert dc.common_columns == common_cols
    assert "A" in dc._completion_cache

    # Test get common
    comps = dc.get_completions(common=True)
    assert len(comps) == 1
    assert comps[0].name == "A"

    # Test get all
    comps_all = dc.get_completions(common=False)
    assert len(comps_all) == 3

    # Test get specific
    comps_spec = dc.get_completions(columns=["B", "C"])
    assert len(comps_spec) == 2
    assert comps_spec[0].name == "B"
