import re


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


__all__ = ["create_duplicate_name"]
