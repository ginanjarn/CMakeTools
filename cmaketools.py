"""cmake tools"""

import json
import threading
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Dict

import sublime
import sublime_plugin
from sublime import HoverZone

from . import api


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
