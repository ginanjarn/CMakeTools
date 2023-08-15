"""sublime settings helper"""

from contextlib import contextmanager
import sublime


@contextmanager
def Settings(
    *, base_name: str = "CMakeTools.sublime-settings", save: bool = False
) -> sublime.Settings:
    """sublime settings"""

    yield sublime.load_settings(base_name)
    if save:
        sublime.save_settings(base_name)
