import json


def format_json_string(json_str: str, indent_step: int = 4, max_width: int = 80) -> str:
    """
    Takes a valid JSON string and returns a formatted string.
    - Indent: `indent_step` spaces.
    - Line wrapping: Enabled only if total chars > `max_width`.
    - Compacts small lists/dicts onto a single line if they fit.
    """
    try:
        # Parse the string into a Python object first
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON string provided.\nDetails: {e}"

    # Helper function for recursive formatting
    def _smart_dump(data, indent_level: int = 0):
        # 1. Generate indentation
        current_indent_str = " " * (indent_level * indent_step)

        # 2. Try compact representation
        compact_repr = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))

        # 3. Check if compact version fits in max_width
        #    (Current Indentation + Length of the string)
        if len(current_indent_str) + len(compact_repr) <= max_width:
            return compact_repr

        # 4. If too long, expand based on type
        if isinstance(data, dict):
            items = []
            next_indent_str = " " * ((indent_level + 1) * indent_step)

            for key, value in data.items():
                formatted_key = json.dumps(str(key), ensure_ascii=False)
                formatted_value = _smart_dump(value, indent_level + 1)
                items.append(f"{next_indent_str}{formatted_key}: {formatted_value}")

            body = ",\n".join(items)
            return "{\n" + body + "\n" + current_indent_str + "}"

        elif isinstance(data, (list, tuple)):
            items = []
            next_indent_str = " " * ((indent_level + 1) * indent_step)

            for item in data:
                formatted_item = _smart_dump(item, indent_level + 1)
                items.append(f"{next_indent_str}{formatted_item}")

            body = ",\n".join(items)
            return "[\n" + body + "\n" + current_indent_str + "]"

        # Fallback for primitives that are too long to wrap (e.g. huge strings)
        return compact_repr

    # Begin the recursive formatting
    return _smart_dump(data)
