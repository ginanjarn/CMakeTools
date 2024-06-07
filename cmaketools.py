"""cmake tools"""

import html
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

import sublime
import sublime_plugin
from sublime import HoverZone

from .api import cmake_help, formatter, diffutils


def valid_context(view: sublime.View, point: int) -> bool:
    return view.match_selector(point, "source.cmake")


def get_workspace_path(view: sublime.View) -> str:
    window = view.window()
    file_name = view.file_name()

    if folders := [
        folder for folder in window.folders() if file_name.startswith(folder)
    ]:
        return max(folders)
    return str(Path(file_name).parent)


class HelpItemManager:
    def __init__(self):
        self.help_cache = cmake_help.HelpCache()

    kind_map = {
        "command": sublime.KIND_FUNCTION,
        "variable": sublime.KIND_VARIABLE,
        "property": sublime.KIND_VARIABLE,
        "module": sublime.KIND_NAMESPACE,
    }

    def get_help(self, name: str) -> str:
        if item := self.help_cache.get_help_item(name):
            doc = self.help_cache.get_cmake_documentation(item.name, item.kind)
            if doc:
                return f"<pre>{html.escape(doc)}</pre>"

        return ""

    def get_completions(self) -> List[sublime.CompletionItem]:
        def to_completion(item: cmake_help.HelpItem):
            if item.kind == "command":
                params = "" if item.name.startswith("end") else "$0"
                snippet = f"{item.name}({params})"

            elif item.kind in {"variable", "property"}:
                snippet = item.name.replace("<", "${1:").replace(">", "}")

            else:
                snippet = item.name

            return sublime.CompletionItem.snippet_completion(
                trigger=item.name,
                kind=self.kind_map[item.kind],
                snippet=snippet,
            )

        return [to_completion(item) for item in self.help_cache.get_help_item_list()]


class ViewEventListener(sublime_plugin.EventListener):
    """"""

    def __init__(self):
        self.help_manager = HelpItemManager()
        self.cached_completions = []

    def on_hover(self, view: sublime.View, point: int, hover_zone: HoverZone):
        # check point in valid source
        if not (valid_context(view, point) and hover_zone == sublime.HOVER_TEXT):
            return

        thread = threading.Thread(target=self._request_help, args=(view, point))
        thread.start()

    def _request_help(self, view: sublime.View, point: int):
        name = view.substr(view.word(point))

        if docstring := self.help_manager.get_help(name):
            view.run_command("markdown_popup", {"text": docstring, "point": point})

    def on_query_completions(
        self, view: sublime.View, prefix: str, locations: List[int]
    ) -> sublime.CompletionList:
        point = locations[0]

        # check point in valid source
        if not valid_context(view, point):
            return

        if items := self.cached_completions:
            return sublime.CompletionList(items)

        thread = threading.Thread(target=self._on_query_completions_task, args=(view,))
        thread.start()
        view.run_command("hide_auto_complete")

    def _on_query_completions_task(self, view: sublime.View):
        self.cached_completions = self.help_manager.get_completions()
        auto_complete_arguments = {
            "disable_auto_insert": True,
            "next_completion_if_showing": True,
            "auto_complete_commit_on_tab": True,
        }
        view.run_command("auto_complete", auto_complete_arguments)


@dataclass
class TextChange:
    region: sublime.Region
    new_text: str
    cursor_move: int = 0

    def moved_region(self, move: int) -> sublime.Region:
        return sublime.Region(self.region.a + move, self.region.b + move)


MULTIDOCUMENT_CHANGE_LOCK = threading.Lock()


class CmaketoolsApplyTextChangesCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit, changes: List[dict]):
        text_changes = [self.to_text_change(c) for c in changes]
        current_sel = list(self.view.sel())

        with MULTIDOCUMENT_CHANGE_LOCK:
            self.apply(edit, text_changes)
            self.relocate_selection(current_sel, text_changes)
            self.view.show(self.view.sel(), show_surrounds=False)

    def to_text_change(self, change: dict) -> TextChange:
        start = change["range"]["start"]
        end = change["range"]["end"]

        start_point = self.view.text_point(start["line"], start["character"])
        end_point = self.view.text_point(end["line"], end["character"])

        region = sublime.Region(start_point, end_point)
        new_text = change["newText"]
        cursor_move = len(new_text) - region.size()

        return TextChange(region, new_text, cursor_move)

    def apply(self, edit: sublime.Edit, text_changes: List[TextChange]):
        cursor_move = 0
        for change in text_changes:
            replaced_region = change.moved_region(cursor_move)
            self.view.erase(edit, replaced_region)
            self.view.insert(edit, replaced_region.a, change.new_text)
            cursor_move += change.cursor_move

    def relocate_selection(
        self, selections: List[sublime.Region], changes: List[TextChange]
    ):
        """relocate current selection following text changes"""
        moved_selections = []
        for selection in selections:
            temp_selection = selection
            for change in changes:
                if temp_selection.begin() > change.region.begin():
                    temp_selection.a += change.cursor_move
                    temp_selection.b += change.cursor_move

            moved_selections.append(temp_selection)

        # we must clear current selection
        self.view.sel().clear()
        self.view.sel().add_all(moved_selections)


class CmaketoolsDocumentFormattingCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit):
        if not self.view.match_selector(0, "source.cmake"):
            print("Only format CMake files")
            return

        text = self.view.substr(sublime.Region(0, self.view.size()))
        formatted = self.format_source(text)

        self.apply_change(edit, text, formatted)

    def format_source(self, text: str) -> str:
        fmt = formatter.CMakeFormatter(text)
        return fmt.format_source()

    def apply_change(self, edit: sublime.Edit, origin: str, formatted: str, /):
        changes = diffutils.get_text_changes(origin, formatted)
        self.view.run_command(
            "cmaketools_apply_text_changes", args={"changes": changes}
        )

    def is_enabled(self) -> bool:
        return self.view and self.view.match_selector(0, "source.cmake")
