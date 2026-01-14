import re
import textwrap

TAB = "    "


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


__all__ = ["wrap_text", "TAB"]
