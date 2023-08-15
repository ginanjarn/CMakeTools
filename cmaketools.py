"""cmake tools"""

import threading
from functools import wraps
from pathlib import Path
from typing import List

import sublime
import sublime_plugin
from sublime import HoverZone

from . import api


def valid_context(view: sublime.View, point: int) -> bool:
    return view.match_selector(point, "source.cmake")


def valid_build(view: sublime.View, point: int = 0):
    return any(
        [
            view.match_selector(point, "source.cmake"),
            view.match_selector(point, "source.c++"),
            view.match_selector(point, "source.c"),
        ]
    )


def get_workspace_path(view: sublime.View) -> str:
    window = view.window()
    file_name = view.file_name()

    if folders := [
        folder for folder in window.folders() if file_name.startswith(folder)
    ]:
        return max(folders)
    return str(Path(file_name).parent)


class ViewEventListener(sublime_plugin.ViewEventListener):
    """"""

    call_lock = threading.Lock()

    def call_once(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if ViewEventListener.call_lock.locked():
                return

            with ViewEventListener.call_lock:
                return func(*args, **kwargs)

        return wrapper

    def on_hover(self, point: int, hover_zone: HoverZone):
        # check point in valid source
        if not (valid_context(self.view, point) and hover_zone == sublime.HOVER_TEXT):
            return

        source = self.view.substr(sublime.Region(0, self.view.size()))
        row, col = self.view.rowcol(point)
        thread = threading.Thread(target=self._request_help, args=(source, row, col))
        thread.start()

    @call_once
    def _request_help(self, source: str, row: int, col: int):
        script = api.Script(source)
        if docstring := script.help(row, col):
            point = self.view.text_point(row, col)
            self.view.run_command("markdown_popup", {"text": docstring, "point": point})

    _previous_cursor_pos = -1
    _cached_completion = None

    def on_query_completions(
        self, prefix: str, locations: List[int]
    ) -> sublime.CompletionList:
        point = locations[0]

        # check point in valid source
        if not valid_context(self.view, point):
            return

        if self._cached_completion:
            if point == self._previous_cursor_pos:
                return sublime.CompletionList(self._cached_completion)

        self._previous_cursor_pos = point
        source = self.view.substr(sublime.Region(0, self.view.size()))
        row, col = self.view.rowcol(point)

        thread = threading.Thread(
            target=self._query_completion, args=(source, row, col)
        )
        thread.start()

    @call_once
    def _query_completion(self, source: str, row: int, col: int):
        script = api.Script(source)
        completions = script.complete(row, col)

        def convert_kind(kind: api.NameType):
            kind_map = {
                api.NameType.Command: sublime.KIND_FUNCTION,
                api.NameType.Module: sublime.KIND_NAMESPACE,
                api.NameType.Property: sublime.KIND_VARIABLE,
                api.NameType.Variable: sublime.KIND_VARIABLE,
            }
            return kind_map[kind]

        def build_completion(name: api.Name) -> sublime.CompletionItem:
            text = name.name
            kind = convert_kind(name.type)
            snippet = text

            if "<" in text:
                snippet = text.replace("<", "${1:").replace(">", "}")

            return sublime.CompletionItem.snippet_completion(
                trigger=text, snippet=snippet, kind=kind
            )

        self._cached_completion = [build_completion(c) for c in completions]

        self.view.run_command(
            "auto_complete",
            {
                "disable_auto_insert": True,
                "next_completion_if_showing": True,
                "auto_complete_commit_on_tab": True,
            },
        )
