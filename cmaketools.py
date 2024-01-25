"""cmake tools"""

import json
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict

import sublime
import sublime_plugin
from sublime import HoverZone

from . import api
from .api import formatter, diffutils


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
        self.cached_helps: Dict[str, api.CMakeHelpItem] = {}
        self.cached_completions: List[sublime.CompletionItem] = []

        self._cache_loaded = False
        self._build_lock = threading.Lock()

    cache_path = Path(__file__).parent.joinpath("var", "cmake_helps.json")
    type_map = {
        "command": sublime.KIND_FUNCTION,
        "variable": sublime.KIND_VARIABLE,
        "property": sublime.KIND_VARIABLE,
        "module": sublime.KIND_NAMESPACE,
    }

    def load_cache(self):
        # call load_cache once only
        self._cache_loaded = True

        if self.cache_path.is_file():
            jstr = self.cache_path.read_text()
            data = json.loads(jstr)

            for item in data:
                self.cached_helps[item["name"]] = api.CMakeHelpItem(
                    item["type"], item["name"]
                )

                if item["type"] == "command":
                    snippet = item["name"] + "($0)"
                else:
                    snippet = item["name"].replace("<", "${1:").replace(">", "}") + "$0"

                self.cached_completions.append(
                    sublime.CompletionItem.snippet_completion(
                        trigger=item["name"],
                        snippet=snippet,
                        kind=self.type_map[item["type"]],
                    )
                )
        else:
            # only one thread can continue
            if self._build_lock.locked():
                return

            with self._build_lock:
                self.build_cache()
                # reload after build
                self.load_cache()

    def build_cache(self):
        cache_dir = self.cache_path.parent
        if not cache_dir.is_dir():
            cache_dir.mkdir(parents=True)

        items = api.get_helps()
        data = [asdict(item) for item in items]
        jstr = json.dumps(data, indent=2)
        self.cache_path.write_text(jstr)

    def get_help(self, name: str) -> Optional[api.CMakeHelpItem]:
        if not self._cache_loaded:
            self.load_cache()

        if item := self.cached_helps.get(name):
            return api.get_docstring(item)

    def get_completions(self):
        if not self._cache_loaded:
            self.load_cache()

        return self.cached_completions()


class ViewEventListener(sublime_plugin.ViewEventListener):
    """"""

    def __init__(self, view: sublime.View):
        super().__init__(view)
        self.help_manager = HelpItemManager()

    def on_hover(self, point: int, hover_zone: HoverZone):
        # check point in valid source
        if not (valid_context(self.view, point) and hover_zone == sublime.HOVER_TEXT):
            return

        thread = threading.Thread(target=self._request_help, args=(point,))
        thread.start()

    def _request_help(self, point):
        name = self.view.substr(self.view.word(point))

        if docstring := self.help_manager.get_help(name):
            self.view.run_command("markdown_popup", {"text": docstring, "point": point})

    def on_query_completions(
        self, prefix: str, locations: List[int]
    ) -> sublime.CompletionList:
        point = locations[0]

        # check point in valid source
        if not valid_context(self.view, point):
            return

        if items := self.help_manager.cached_completions:
            return sublime.CompletionList(items)

        thread = threading.Thread(target=self.help_manager.load_cache)
        thread.start()


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
