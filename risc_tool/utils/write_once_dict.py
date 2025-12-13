import typing as t
from collections import OrderedDict

K = t.TypeVar("K")
V = t.TypeVar("V")


class WriteOnceOrderedDict(OrderedDict[K, V]):
    """
    An OrderedDict that allows adding new keys but forbids
    modifying existing values, deleting keys, or reordering.
    """

    def __setitem__(self, key: K, value: V):
        if key in self:
            raise ValueError(f"Key '{key}' already exists. Modification is forbidden.")
        super().__setitem__(key, value)

    def __delitem__(self, key: K):
        raise ValueError("Deletion is forbidden.")

    # --- Blocking other mutation methods ---

    def pop(self, key: K, *args, **kwargs):
        raise ValueError("Deletion (pop) is forbidden.")

    def popitem(self, last=True):
        raise ValueError("Deletion (popitem) is forbidden.")

    def clear(self):
        raise ValueError("Deletion (clear) is forbidden.")

    def move_to_end(self, key: K, last=True):
        raise ValueError("Reordering (move_to_end) is forbidden.")

    def update(self, *args, **kwargs):
        # Check args (dictionary or iterable)
        if args:
            if len(args) > 1:
                raise TypeError(f"update expected at most 1 arguments, got {len(args)}")
            other = dict(args[0])  # type: ignore
            for key in other:
                if key in self:
                    raise ValueError(f"Key '{key}' already exists. Update forbidden.")

        # Check kwargs
        for key in kwargs:
            if key in self:
                raise ValueError(f"Key '{key}' already exists. Update forbidden.")

        super().update(*args, **kwargs)
