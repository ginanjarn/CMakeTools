from pathlib import Path

import sublime


def get_workspace_path(view: sublime.View) -> Path:
    """get workspace path
    Use directory contain 'CMakeLists.txt' as workspace path.

    Raise FileNotFoundError if not found.
    """

    file_name = Path(view.file_name())
    folders = [
        folder
        for folder in view.window().folders()
        if str(file_name).startswith(folder)
    ]

    # sort form shortest path
    folders.sort()
    # set first folder contain 'CMakeLists.txt' as workspace path
    for folder in folders:
        path = Path(folder, "CMakeLists.txt")
        if path.is_file():
            return path.parent

    raise FileNotFoundError("unable find 'CMakeLists.txt'")
