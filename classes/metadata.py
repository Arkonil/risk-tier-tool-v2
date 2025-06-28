from dataclasses import dataclass, field

import numpy as np


@dataclass
class Variable:
    id: int
    name: str
    dtype: np.dtype


@dataclass
class Metadata:
    variables: list[Variable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "variables": [
                {"id": var.id, "name": var.name, "dtype": str(var.dtype)}
                for var in self.variables
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Metadata":
        variables = [
            Variable(id=var["id"], name=var["name"], dtype=np.dtype(var["dtype"]))
            for var in data.get("variables", [])
        ]
        return cls(variables=variables)


__all__ = [
    "Variable",
    "Metadata",
]
