import typing as t
from dataclasses import dataclass, field

import numpy as np

@dataclass
class Variable:
    id: int
    name: str
    dtype: np.dtype
    
    
@dataclass
class Metadata:
    variables: t.List[Variable] = field(default_factory=list)
