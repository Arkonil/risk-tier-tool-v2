from risc_tool.data.models.enums import VariableType, StrEnumMeta

def test_variable_type_other():
    vt = VariableType.NUMERICAL
    assert vt.other == VariableType.CATEGORICAL
    
    vt2 = VariableType.CATEGORICAL
    assert vt2.other == VariableType.NUMERICAL

def test_strenum_meta_contains():
    # StrEnumMeta implements __contains__ using try/except on constructor
    assert "Numerical" in VariableType
    assert "Invalid" not in VariableType
