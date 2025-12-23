import hashlib

import pandas as pd


def hash_boolean_series(s: pd.Series) -> str:
    """
    Generates a SHA-256 hash for a pandas boolean Series.

    The hash value is dependent on both the values within the Series and the
    size of the Series. Any change to the data or the length will result
    in a different hash.

    Args:
        s: A pandas Series with a boolean data type.

    Returns:
        A hexadecimal string representing the SHA-256 hash of the Series.

    Raises:
        TypeError: If the input is not a pandas Series or does not have a
                   boolean dtype.
    """
    if not isinstance(s, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    if not pd.api.types.is_bool_dtype(s):
        raise TypeError("Series dtype must be boolean.")

    # Create a new hash object
    hasher = hashlib.sha256()

    # Convert the Series' boolean values to a byte string.
    # The underlying numpy array's tobytes() method is efficient for this.
    series_bytes = s.to_numpy().tobytes()

    # Update the hash object with the bytes from the series values.
    # This ensures the hash changes if any value changes.
    hasher.update(series_bytes)

    # To ensure the hash also changes with the size, we can explicitly
    # include the series length in the hash calculation.
    # We convert the length to a string and then encode it to bytes.
    size_bytes = str(len(s)).encode("utf-8")
    hasher.update(size_bytes)

    # Return the hexadecimal representation of the hash
    return hasher.hexdigest()


__all__ = ["hash_boolean_series"]
