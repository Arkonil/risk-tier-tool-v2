from code_editor import code_editor


def query_editor(current_query: str, column_completions: list[dict[str, str | int]]):
    code_editor_output = code_editor(
        # key="code_editor",
        code=current_query,
        lang="python",
        completions=column_completions,
        replace_completer=True,
        keybindings="vscode",
        props={
            "minLines": 13,
            "fontSize": 16,
            "enableSnippets": False,
            "debounceChangePeriod": 100,
        },
        options={
            "showLineNumbers": True,
        },
        response_mode="debounce",
    )

    return code_editor_output
