"""panels"""

import sublime


class OutputPanel:
    """"""

    def __init__(self):
        self.panel_name = "cmaketools"
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
        self.panel.set_read_only(False)

    def move_cursor(self, point: int = -1) -> None:
        """move cursor
        * move to the end if point < 0
        """
        point = point if point >= 0 else self.panel.size()

        self.panel.sel().clear()
        self.panel.sel().add(point)

    def show(self, *, clear: bool = False) -> None:
        """show panel"""
        # ensure panel is created
        self.create_panel()

        if clear:
            self.clear()

        self.window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

    def clear(self) -> None:
        if not self.panel:
            return

        self.panel.run_command("select_all")
        self.panel.run_command("left_delete")

    def write(self, s: str) -> int:
        # Create panel if not exists.
        self.create_panel()

        end_point = self.panel.size()
        # User may select text on panel, move cursor to the end.
        self.move_cursor(end_point)
        # User may scrolled up the panel.
        self.panel.show(end_point, keep_to_left=True)

        self.panel.run_command("insert", {"characters": s})
        return len(s)
