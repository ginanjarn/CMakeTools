"""cmake tools"""

import os
import threading
from pathlib import Path
from functools import wraps
from typing import List

import sublime
import sublime_plugin
from sublime import HoverZone

from . import api
from .api import cmake_build, quickstart_generator, compiler_kit


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

    # project_configured = False

    # def on_activated(self):
    #     if not valid_context(self.view, 0):
    #         return

    #     if self.project_configured:
    #         return

    #     self.view.run_command("cmaketools_configure")
    #     self.project_configured = True


CC_KEY = "c"
CXX_KEY = "cxx"
GENERATOR_KEY = "generator"


class Preferences:
    """preference manager"""

    base_name = "CMakeTools.sublime-settings"

    def load_settings(self):
        return sublime.load_settings(self.base_name)

    def save_settings(self):
        return sublime.save_settings(self.base_name)

    def set_compiler(self, compiler: compiler_kit.Compiler):
        self.c_compiler = compiler.cc
        self.cxx_compiler = compiler.cxx
        self.generator = compiler.generator

    @property
    def c_compiler(self):
        return self.load_settings().get(CC_KEY)

    @c_compiler.setter
    def c_compiler(self, value):
        self.load_settings().set(CC_KEY, value)
        self.save_settings()

    @property
    def cxx_compiler(self):
        return self.load_settings().get(CXX_KEY)

    @cxx_compiler.setter
    def cxx_compiler(self, value):
        self.load_settings().set(CXX_KEY, value)
        self.save_settings()

    @property
    def generator(self):
        return self.load_settings().get(GENERATOR_KEY)

    @generator.setter
    def generator(self, value):
        self.load_settings().set(GENERATOR_KEY, value)
        self.save_settings()


PREFERENCES = Preferences()

SELECT_COMPILER_EVENT = threading.Event()


class CmaketoolsSelectCompilerCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        thread = threading.Thread(target=self._set_compiler)
        thread.start()

    @staticmethod
    def _build_title(c: compiler_kit.Compiler) -> str:
        return f"({c.name.upper()}) {c.cc}"

    def _set_compiler(self):

        try:
            sublime.status_message("scanning installed compilers...")
            scanner = compiler_kit.Scanner()
            compilers = scanner.scan()

        except Exception:
            SELECT_COMPILER_EVENT.set()

        def select_compiler(index=-1):
            try:
                if index < 0:
                    return
                PREFERENCES.set_compiler(compilers[index])
            finally:
                SELECT_COMPILER_EVENT.set()

        if not compilers:
            return

        compiler_titles = [self._build_title(c) for c in compilers]

        self.view.window().show_quick_panel(
            compiler_titles,
            on_select=select_compiler,
            flags=sublime.MONOSPACE_FONT,
            placeholder="Select compiler...",
        )


class CmaketoolsConfigureCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        thread = threading.Thread(target=self._configure)
        thread.start()

    is_compiler_selected = False

    def _select_compiler(self):
        self.is_compiler_selected = True
        self.view.run_command("cmaketools_select_compiler")

    def _remove_cmakecache(self, workspace_path: Path):
        # only remove "CMakeCache.txt" file in nearest workspace_path
        for path in Path(workspace_path).glob("*/CMakeCache.txt"):
            print(f"remove {path}")
            os.remove(path)

    def _configure(self):
        workspace_path = get_workspace_path(self.view)
        c_compiler = PREFERENCES.c_compiler
        cxx_compiler = PREFERENCES.cxx_compiler
        generator = PREFERENCES.generator

        if not all([c_compiler, cxx_compiler, generator]):
            if self.is_compiler_selected:
                # exit function to prevent '_configure()' infinity call
                return

            self._select_compiler()

            SELECT_COMPILER_EVENT.wait(30)
            # cmake configuration not changed if "CMakeCache.txt" not removed
            self._remove_cmakecache(workspace_path)
            # reconfigure after compiler selected
            self._configure()
            return

        try:
            cmake_build.configure(
                source_dir=workspace_path,
                cc_path=c_compiler,
                cxx_path=cxx_compiler,
                generator=generator,
            )
        except Exception as err:
            print(err)

    def is_visible(self):
        return valid_build(self.view)


class CmaketoolsBuildCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, build_type: str = ""):
        if build_type:
            self._build(build_type)
        else:
            self.select_build_type()

    def select_build_type(self):
        build_types = cmake_build.BUILD_TYPES

        def build_with_type(index):
            if index < 0:
                return
            self._build(build_types[index])

        self.view.window().show_quick_panel(
            build_types, selected_index=0, on_select=build_with_type
        )

    def _build(self, build_type):
        workspace_path = get_workspace_path(self.view)

        thread = threading.Thread(
            target=cmake_build.build,
            kwargs={
                "build_dir": str(Path(workspace_path).joinpath("build")),
                "build_type": build_type,
            },
        )
        thread.start()

    def is_visible(self):
        return valid_build(self.view)


class CmaketoolsCtestCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, build_type: str = ""):
        workspace_path = get_workspace_path(self.view)
        thread = threading.Thread(
            target=cmake_build.ctest,
            kwargs={"source_dir": workspace_path, "build_type": build_type},
        )
        thread.start()

    def is_visible(self):
        return valid_build(self.view)


class CmaketoolsQuickstartCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, project_type: str = ""):

        self.workspace_path = get_workspace_path(self.view)
        self.project_type = project_type
        self.project_name = ""

        self.get_projecttype_event = threading.Event()
        self.input_projectname_event = threading.Event()

        thread = threading.Thread(target=self.build_steps)
        thread.start()

    def build_steps(self):

        self.get_project_type()
        self.get_projecttype_event.wait()
        if not self.project_type:
            return

        self.input_project_name()
        self.input_projectname_event.wait()
        if not self.project_name:
            return

        self.generate()

    def input_project_name(self):
        def set_project_name(name):
            if name:
                self.project_name = name
            self.input_projectname_event.set()

        preferred_name = Path(self.workspace_path).name
        self.view.window().show_input_panel(
            "Project name", preferred_name, set_project_name, None, None
        )

    def get_project_type(self):
        project_types = quickstart_generator.PROJECT_TYPES

        def select_type(index):
            if index > -1:
                self.project_type = project_types[index]
            self.get_projecttype_event.set()

        self.view.window().show_quick_panel(project_types, select_type)

    def generate(self):

        quickstart_generator.generate_quickstart(
            workspace_path=self.workspace_path,
            project_type=self.project_type,
            project_name=self.project_name,
        )

    def is_visible(self):
        return valid_build(self.view)
