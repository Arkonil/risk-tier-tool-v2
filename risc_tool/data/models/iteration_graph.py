from pydantic import BaseModel, ConfigDict, Field

from risc_tool.data.models.types import IterationID


class IterationGraph(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        validate_by_alias=True,
        arbitrary_types_allowed=True,
    )
    connections: dict[IterationID, list[IterationID]] = Field(default_factory=dict)

    def add_child(self, parent_id: IterationID, child_id: IterationID):
        if parent_id not in self.connections:
            self.connections[parent_id] = []

        self.connections[parent_id].append(child_id)

    def get_parent(self, iteration_id: IterationID) -> IterationID | None:
        for parent, children in self.connections.items():
            if iteration_id in children:
                return parent

        return None

    def iteration_depth(self, iteration_id: IterationID) -> int:
        parent_iteration_id: IterationID | None = self.get_parent(iteration_id)
        if parent_iteration_id is None:
            return 1

        return 1 + self.iteration_depth(parent_iteration_id)

    def get_ancestors(self, iteration_id: IterationID) -> list[IterationID]:
        ancestors: list[IterationID] = []
        parent_iteration_id: IterationID | None = self.get_parent(iteration_id)
        while parent_iteration_id is not None:
            ancestors.append(parent_iteration_id)
            parent_iteration_id = self.get_parent(parent_iteration_id)

        return list(reversed(ancestors))

    def get_descendants(self, iteration_id: IterationID) -> list[IterationID]:
        if iteration_id not in self.connections:
            return []

        descendants: list[IterationID] = self.connections[iteration_id]
        for descendant in descendants:
            descendants += self.get_descendants(descendant)

        return descendants

    def get_root_iter_id(self, iteration_id: IterationID) -> IterationID:
        parent_iteration_id: IterationID | None = self.get_parent(iteration_id)

        if parent_iteration_id is None:
            return iteration_id

        return self.get_root_iter_id(parent_iteration_id)

    def is_root(self, iteration_id: IterationID) -> bool:
        return self.get_parent(iteration_id) is None

    def is_leaf(self, iteration_id: IterationID) -> bool:
        return (
            iteration_id not in self.connections
            or len(self.connections[iteration_id]) == 0
        )


__all__ = [
    "IterationGraph",
]
