import pandas as pd
import numpy as np
from risc_tool.data.models.defaults import DefaultOptions

def test_default_options_singleton():
    d1 = DefaultOptions()
    d2 = DefaultOptions()
    assert d1 is d2

def test_default_options_properties():
    do = DefaultOptions()
    
    assert isinstance(do.risk_segment_details, pd.DataFrame)
    assert not do.risk_segment_details.empty
    
    assert do.max_iteration_depth == 10
    assert do.max_categorical_unique == 20
    
    meta = do.default_iteation_metadata
    assert meta.editable is True
    assert meta.scalars_enabled is True
