import pytest
from pydantic import ValidationError

from risc_tool.data.models.completion import Completion


def test_completion_creation():
    c = Completion(caption="cap", value="val", meta="meta", name="name", score=100)
    assert c.caption == "cap"
    assert c.value == "val"
    assert c.score == 100


def test_completion_validation():
    with pytest.raises(ValidationError):
        Completion(
            caption="cap", value="val", meta="meta", name="name", score="not_an_int"
        )
