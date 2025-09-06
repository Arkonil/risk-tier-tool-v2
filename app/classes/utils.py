import hashlib
import re
import textwrap

import pandas as pd


def integer_generator():
    current = 0
    while True:
        current += 1
        yield current


def wrap_text(text: str, **kwargs) -> list[str]:
    """
    Wraps text to a specified width, preserving content within double quotes.
    """
    # Find all quoted sections
    quoted_sections = re.findall(r"\"(.*?)\"", text)

    # Replace quoted sections with placeholders to avoid wrapping them
    quote_placeholder_map = {}
    for i, quoted_text in enumerate(quoted_sections):
        placeholder = f"__QUOTE_PLACEHOLDER_{i}__"
        quote_placeholder_map[placeholder] = quoted_text
        text = text.replace(
            f'"{quoted_text}"', placeholder, 1
        )  # Replace only first occurrence

    # Wrap the remaining text (non-quoted parts)
    wrapped_text = textwrap.fill(text, **kwargs)

    # Restore the quoted sections
    for placeholder, original_quoted_text in quote_placeholder_map.items():
        wrapped_text = wrapped_text.replace(placeholder, f'"{original_quoted_text}"')

    return wrapped_text.splitlines()


def create_duplicate_name(name: str, existing_names: set[str]) -> str:
    """
    Generates a unique duplicate name based on the existing names.

    Args:
        name (str): The original name to duplicate.
        existing_names (set[str]): A set of existing names to avoid duplicates.

    Returns:
        str: A unique duplicate name.
    """
    if match := re.match(r"^(.*) - copy\((\d+)\)?$", name):
        base_name = match.group(1)
        copy_number = int(match.group(2)) + 1
    elif name.endswith(" - copy"):
        base_name = name[:-7]
        copy_number = 2
    else:
        base_name = name
        copy_number = 1

    new_name = f"{base_name} - copy({copy_number})"
    while new_name in existing_names:
        copy_number += 1
        new_name = f"{base_name} - copy({copy_number})"

    return new_name


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
    if s.dtype != "bool":
        raise TypeError("Series dtype must be boolean.")

    # Create a new hash object
    hasher = hashlib.sha256()

    # Convert the Series' boolean values to a byte string.
    # The underlying numpy array's tobytes() method is efficient for this.
    series_bytes = s.values.tobytes()

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
