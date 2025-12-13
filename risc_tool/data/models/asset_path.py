import pathlib

MODULE_NAME = "risc_tool"


class AssetPath:
    FILTER_QUERY_REFERENCE = pathlib.Path(
        f"{MODULE_NAME}/assets/filter_query_reference.md"
    )
    APP_ICON = pathlib.Path(f"{MODULE_NAME}/assets/rt-icon.svg")
    APP_LOGO_LIGHT = pathlib.Path(f"{MODULE_NAME}/assets/rt-logo-light.svg")
    APP_LOGO_DARK = pathlib.Path(f"{MODULE_NAME}/assets/rt-logo-dark.svg")
    NO_DATA_ERROR_ICON = pathlib.Path(f"{MODULE_NAME}/assets/no-data-error.svg")
    NO_FILTER_ICON = pathlib.Path(f"{MODULE_NAME}/assets/no-filter.svg")
    NO_METRIC_ICON = pathlib.Path(f"{MODULE_NAME}/assets/no-metric.svg")
    NO_ITERATION_ICON = pathlib.Path(f"{MODULE_NAME}/assets/no-iteration.svg")
    STYLESHEET = pathlib.Path(f"{MODULE_NAME}/assets/style.css")
    ARROW_RIGHT = pathlib.Path(f"{MODULE_NAME}/assets/arrow-right.svg")
    SESSION_EXPORT_DOC = pathlib.Path(f"{MODULE_NAME}/assets/session_export_doc.md")


__all__ = ["AssetPath"]
