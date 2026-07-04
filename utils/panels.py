"""panels"""

from contextlib import contextmanager
import sublime


@contextmanager
def mutable_view(view: sublime.View) -> sublime.View:
    if not view:
        raise Exception("view not created yet")

    try:
        view.set_read_only(False)
        yield view
    finally:
        view.set_read_only(True)


class OutputPanel:
    """"""

    def __init__(self, panel_name: str):
        self.panel_name = panel_name
        self.panel: sublime.View = None

    @property
    def window(self) -> sublime.Window:
        return sublime.active_window()

    def create_panel(self) -> None:
        if self.panel and self.panel.is_valid():
            return

        self.panel = self.window.create_output_panel(self.panel_name)

        settings = {
            "gutter": False,
            "auto_indent": False,
            "word_wrap": False,
        }
        self.panel.settings().update(settings)

    def seek_end(self, view: sublime.View) -> None:
        """seek cursor to end"""
        view.sel().clear()
        view.sel().add(view.size())

    def show(self) -> None:
        """show panel"""
        self.create_panel()
        self.window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

    def clear(self) -> None:
        with mutable_view(self.panel) as view:
            view.run_command("select_all")
            view.run_command("left_delete")

    def write(self, s: str) -> int:
        with mutable_view(self.panel) as view:
            self.seek_end(view)
            view.run_command("insert", {"characters": s})
            view.show(view.size(), keep_to_left=True)

        return len(s)
