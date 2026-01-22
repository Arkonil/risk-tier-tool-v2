import pytest

from risc_tool.data.models.iteration_graph import IterationGraph
from risc_tool.data.models.types import IterationID


@pytest.fixture
def graph():
    # Struct: 1 -> 2, 1 -> 3, 2 -> 4
    # Depth: 1(1), 2(2), 3(2), 4(3)
    g = IterationGraph()
    g.add_child(IterationID(1), IterationID(2))
    g.add_child(IterationID(1), IterationID(3))
    g.add_child(IterationID(2), IterationID(4))
    return g


def test_graph_structure(graph):
    # Connections
    assert IterationID(2) in graph.connections[IterationID(1)]
    assert IterationID(4) in graph.connections[IterationID(2)]


def test_get_parent(graph):
    assert graph.get_parent(IterationID(2)) == IterationID(1)
    assert graph.get_parent(IterationID(4)) == IterationID(2)
    assert graph.get_parent(IterationID(1)) is None


def test_iteration_depth(graph):
    assert graph.iteration_depth(IterationID(1)) == 1
    assert graph.iteration_depth(IterationID(2)) == 2
    assert graph.iteration_depth(IterationID(3)) == 2
    assert graph.iteration_depth(IterationID(4)) == 3


def test_get_ancestors(graph):
    assert graph.get_ancestors(IterationID(1)) == []
    assert graph.get_ancestors(IterationID(2)) == [IterationID(1)]
    assert graph.get_ancestors(IterationID(4)) == [IterationID(1), IterationID(2)]


def test_get_descendants(graph):
    # descendants of 1: 2, 3, 4
    desc = graph.get_descendants(IterationID(1))
    assert set(desc) == {IterationID(2), IterationID(3), IterationID(4)}

    desc_2 = graph.get_descendants(IterationID(2))
    assert set(desc_2) == {IterationID(4)}


def test_root_id(graph):
    assert graph.get_root_iter_id(IterationID(4)) == IterationID(1)
    assert graph.get_root_iter_id(IterationID(3)) == IterationID(1)
    assert graph.get_root_iter_id(IterationID(1)) == IterationID(1)


def test_is_leaf(graph):
    assert not graph.is_leaf(IterationID(1))
    assert not graph.is_leaf(IterationID(2))
    assert graph.is_leaf(IterationID(3))
    assert graph.is_leaf(IterationID(4))
