class SentinelInt(int):
    # 1. Declare the field here so Pylance knows it exists
    _name: str | None = None

    def __new__(cls, value: int = 0, name: str | None = None):
        # Create the int instance
        obj = super().__new__(cls, value)
        # Store the name directly on the object
        # If it has a name, we treat it as a sentinel
        obj._name = name
        return obj

    def __eq__(self, other):
        # Check if 'self' is a sentinel by checking its _name attribute
        # getattr is safe and won't trigger recursion
        is_self_sentinel = getattr(self, "_name", None) is not None

        # Check if 'other' is a sentinel
        is_other_sentinel = getattr(other, "_name", None) is not None

        # If EITHER is a sentinel, we enforce Identity Comparison
        if is_self_sentinel or is_other_sentinel:
            # Returns True only if they are the exact same object in memory
            return self._name == other._name

        # Otherwise, perform standard integer comparison
        return super().__eq__(other)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        # If it has a name, print the name
        name = getattr(self, "_name", None)
        if name:
            return f"<{name}>"
        return super().__repr__()

    def __hash__(self):
        # Allow these to be used in sets/dicts
        return super().__hash__()


__all__ = ["SentinelInt"]
