"""cmake tools"""

import html
import json
import threading
from pathlib import Path
from typing import List, Dict

import sublime
import sublime_plugin
from sublime import HoverZone

from .internal.cmake_help import Name, NameType, HelpCLI


_TYPE_MAP = {
    NameType.Command: (sublime.KindId.FUNCTION, "", ""),
    NameType.Module: (sublime.KindId.NAMESPACE, "", ""),
    NameType.Policy: (sublime.KindId.COLOR_ORANGISH, "v", ""),
    NameType.Property: (sublime.KindId.VARIABLE, "", ""),
    NameType.Variable: (sublime.KindId.VARIABLE, "", ""),
}


def nametype_to_kind(type: NameType) -> tuple:
    return _TYPE_MAP[type]


def is_valid_context(view: sublime.View, point: int) -> bool:
    return view.match_selector(point, "source.cmake")


class CMakeHelpCache:
    """"""

    def __init__(self):
        self.name_map: Dict[str, Name] = {}
        self.help_cli = HelpCLI(".")

        self.is_cache_loaded = False

    cache_path = Path().home().joinpath(".CMakeTools/help_cache.json")

    def load_cache(self):
        self.is_cache_loaded = True
        try:
            text = self.cache_path.read_text()
            data = json.loads(text)
            name_map = {item["name"]: Name(**item) for item in data["items"]}
            self.name_map = name_map

        except Exception:
            cmake_names = self._fetch_names()
            self._write_cache(cmake_names)
            self.name_map = {cmake_name.name: cmake_name for cmake_name in cmake_names}

    def _fetch_names(self) -> List[Name]:
        return list(self.help_cli.get_name_list())

    def _write_cache(self, name_list: List[Name]):
        # create parent directory if not exists
        parent = self.cache_path.parent
        parent.mkdir(parents=True, exist_ok=True)

        def to_dict(name: Name):
            return {"name": name.name, "type": name.type.value}

        data = {"items": [to_dict(name) for name in name_list]}
        json_str = json.dumps(data, indent=2)
        self.cache_path.write_text(json_str)

    def get_completions(self) -> List[Name]:
        """"""
        if not self.is_cache_loaded:
            self.load_cache()

        result = self.help_cli.get_name_list()
        return result

    def get_documentation(self, name: str) -> str:
        """"""
        if not self.is_cache_loaded:
            self.load_cache()

        if cmake_name := self.name_map.get(name):
            return self.help_cli.get_documentation(cmake_name)
        return ""


class CMakeHelpManager:
    def __init__(self):
        self.help_cache = CMakeHelpCache()
        self.completion_cache = None

    def get_help(self, name: str) -> str:
        """"""
        if doc := self.help_cache.get_documentation(name):
            return f"<pre>{html.escape(doc)}</pre>"

        return ""

    def get_completion(self) -> List[sublime.CompletionItem]:
        if cache := self.completion_cache:
            return cache

        temp = self._get_completion()
        self.completion_cache = temp
        return temp

    def _get_completion(self) -> List[sublime.CompletionItem]:
        """"""

        def to_completion(item: Name):
            if item.type == NameType.Command:
                params = "" if item.name.startswith("end") else "$0"
                snippet = f"{item.name}({params})"

            elif item.type in {NameType.Variable, NameType.Property}:
                snippet = item.name.replace("<", "${1:").replace(">", "}")

            else:
                snippet = item.name

            return sublime.CompletionItem.snippet_completion(
                trigger=item.name,
                kind=nametype_to_kind(item.type),
                snippet=snippet,
            )

        return [to_completion(item) for item in self.help_cache.get_completions()]


class ViewEventListener(sublime_plugin.EventListener):
    """"""

    def __init__(self):
        self.help_manager = CMakeHelpManager()
        self.cached_completions = []

    def on_hover(self, view: sublime.View, point: int, hover_zone: HoverZone):
        # check point in valid source
        if not (is_valid_context(view, point) and hover_zone == sublime.HOVER_TEXT):
            return

        thread = threading.Thread(target=self._on_hover_task, args=(view, point))
        thread.start()

    def _on_hover_task(self, view: sublime.View, point: int):
        name = view.substr(view.word(point))

        if docstring := self.help_manager.get_help(name):
            view.run_command(
                "marked_popup",
                {"text": docstring, "location": point, "markup": "markdown"},
            )

    def on_query_completions(
        self, view: sublime.View, prefix: str, locations: List[int]
    ) -> sublime.CompletionList:
        point = locations[0]

        # check point in valid source
        if not is_valid_context(view, point):
            return

        if items := self.cached_completions:
            return sublime.CompletionList(items)

        thread = threading.Thread(target=self._on_query_completions_task, args=(view,))
        thread.start()
        view.run_command("hide_auto_complete")

    def _on_query_completions_task(self, view: sublime.View):
        self.cached_completions = self.help_manager.get_completion()
        auto_complete_arguments = {
            "disable_auto_insert": True,
            "next_completion_if_showing": True,
            "auto_complete_commit_on_tab": True,
        }
        view.run_command("auto_complete", auto_complete_arguments)
