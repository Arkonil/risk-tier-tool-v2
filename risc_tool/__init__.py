from risc_tool.config.page_config import set_page_config
from risc_tool.config.session_state import set_session_state
from risc_tool.pages.navigation import set_page_navigation


def run_app(debug_mode: bool = False):
    set_page_config()
    set_session_state()
    set_page_navigation()


__all__: list[str] = ["run_app"]
