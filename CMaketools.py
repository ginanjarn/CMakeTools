"""CMaketools main implementation"""

import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Iterable, Optional, Any

import sublime
import sublime_plugin

from .api import build_generator
from .api import cmake_script

from .third_party import mistune

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)  # module logging level
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)


@dataclass(order=True)
class Project:
    path: str = ""
    name: str = ""
    project_type: str = ""
    generator: str = ""
    c_path: str = ""
    cxx_path: str = ""
    build_mode: str = build_generator.MODE_DEBUG


class CmakeToolsCreateProjectCommand(sublime_plugin.TextCommand):
    project: Project = Project()

    def run(self, edit: sublime.Edit):
        self.select_folder()

    def select_folder(self):
        window: sublime.Window = self.view.window()
        folders = window.folders()

        def select_folder(index=-1):
            if index < 0:
                return

            self.project.path = folders[index]
            self.project.name = os.path.basename(folders[index])
            self.select_project_type()

        if len(folders) == 0:
            # do nothing
            pass
        elif len(folders) == 1:
            # select working folder
            select_folder(0)
        else:
            # show option
            window.show_quick_panel(
                items=folders, on_select=select_folder, flags=sublime.MONOSPACE_FONT
            )

    def select_project_type(self):
        project_types = [build_generator.TYPE_EXECUTABLE, build_generator.TYPE_LIBRARY]

        def on_select(index=-1):
            if index < 0:
                return

            self.project.project_type = project_types[index]
            self.generate_snippet()

        window: sublime.Window = self.view.window()
        window.show_quick_panel(
            items=project_types, on_select=on_select, flags=sublime.MONOSPACE_FONT
        )

    def generate_snippet(self):
        def generate():
            try:
                build_generator.create_project_snippet(
                    self.project.path, self.project.name, self.project.project_type
                )
            except Exception as err:
                LOGGER.error(f"Generate snippet error\n--> {err}")

        thread = threading.Thread(target=generate)
        thread.start()


class WindowStatus:
    _key = "cmaketools"

    @staticmethod
    def set(message: str):
        view = sublime.active_window().active_view()
        view.set_status(WindowStatus._key, f"CMakeTools: {message}. ")

    @staticmethod
    def clear():
        for view in sublime.active_window().views():
            view.erase_status(WindowStatus._key)


class CmakeToolsGenerateProjectCommand(sublime_plugin.TextCommand):
    project: Project = Project()

    def run(self, edit: sublime.Edit):
        self.select_folder()

    def select_folder(self):
        window: sublime.Window = self.view.window()
        folders = window.folders()

        def _select_folder(index=-1):
            if index < 0:
                return

            self.project.path = folders[index]
            self.project.name = os.path.basename(folders[index])
            self.select_compiler()

        if len(folders) == 0:
            # do nothing
            pass

        elif len(folders) == 1:
            # select working folder
            _select_folder(0)

        else:
            # show option
            window.show_quick_panel(
                items=folders, on_select=_select_folder, flags=sublime.MONOSPACE_FONT
            )

    def select_compiler(self):

        compilers = build_generator.get_compilers()
        compiler_names = [compiler.name for compiler in compilers]

        def _select_compiler(index=-1):
            if index < 0:
                return

            compiler = compilers[index]
            self.project.c_path = compiler.c_path
            self.project.cxx_path = compiler.cxx_path

            self.select_generator()

        window: sublime.Window = self.view.window()
        window.show_quick_panel(
            items=compiler_names,
            on_select=_select_compiler,
            flags=sublime.MONOSPACE_FONT,
        )

    def select_generator(self):
        generators = build_generator.get_generators()

        def _select_generator(index=-1):
            if index < 0:
                return
            self.project.generator = generators[index]

            self.generate_project()

        window: sublime.Window = self.view.window()
        window.show_quick_panel(
            items=generators, on_select=_select_generator, flags=sublime.MONOSPACE_FONT
        )

    def offer_create_snippet(self, text: str):
        found = re.search("does not appear to contain CMakeLists.txt", text)
        if found:
            title = "Project error"
            message = (
                "CMakeLists.txt not found in project directory.\nCreate new project?"
            )
            is_create = sublime.yes_no_cancel_dialog(
                message, yes_title="Yes", no_title="No", title=title
            )
            if is_create:
                self.view.run_command("cmake_tools_create_project")

    def generate_project(self):
        def generate():
            LOGGER.debug("generate")
            try:
                WindowStatus.set("generate project")
                result = build_generator.generate_project(
                    self.project.path,
                    generator=self.project.generator,
                    c_path=self.project.c_path,
                    cxx_path=self.project.cxx_path,
                )
            except Exception as err:
                LOGGER.error(f"generate project error --> {err}")
            else:
                print(result)
                self.offer_create_snippet(result)
            finally:
                LOGGER.debug("finish generate")
                WindowStatus.clear()

        thread = threading.Thread(target=generate)
        thread.start()


class CmakeToolsBuildProjectCommand(sublime_plugin.TextCommand):
    project: Project = Project()

    def run(self, edit: sublime.Edit):
        self.select_folder()

    def select_folder(self):
        window: sublime.Window = self.view.window()
        folders = window.folders()

        def _select_folder(index=-1):
            if index < 0:
                return

            self.project.path = folders[index]
            self.select_mode()

        if len(folders) == 0:
            # do nothing
            pass

        elif len(folders) == 1:
            # select working folder
            _select_folder(0)

        else:
            # show option
            window.show_quick_panel(
                items=folders, on_select=_select_folder, flags=sublime.MONOSPACE_FONT
            )

    def select_mode(self):
        modes = [build_generator.MODE_DEBUG, build_generator.MODE_RELEASE]

        def _select_mode(index=-1):
            if index < 0:
                return
            self.project.build_mode = modes[index]
            self.build_project()

        window: sublime.Window = self.view.window()
        window.show_quick_panel(
            items=modes, on_select=_select_mode, flags=sublime.MONOSPACE_FONT
        )

    def build_project(self):
        def build():
            LOGGER.debug("start build")
            try:
                WindowStatus.set("build project")
                result = build_generator.build(
                    self.project.path, self.project.build_mode
                )
            except Exception as err:
                LOGGER.error(f"build error --> {err}")
            else:
                print(result)
            finally:
                LOGGER.debug("finish build")
                WindowStatus.clear()

        thread = threading.Thread(target=build)
        thread.start()


PIPE_LOCK = threading.Lock()


def pipe(func):
    def wrapper(*args, **kwargs):
        if PIPE_LOCK.locked():
            return None

        with PIPE_LOCK:
            return func(*args, **kwargs)

    return wrapper


def is_cmake_code(view: sublime.View):
    """view is cmake code"""

    if valid := view.match_selector(0, "source.cmake"):
        return valid
    if valid := view.match_selector(0, "source.cmakecache"):
        return valid

    return False


KIND_MAP = {
    cmake_script.NameKind.COMMAND.value: sublime.KIND_FUNCTION,
    cmake_script.NameKind.MODULE.value: sublime.KIND_NAMESPACE,
    cmake_script.NameKind.POLICY.value: sublime.KIND_VARIABLE,
    cmake_script.NameKind.PROPERTY.value: sublime.KIND_VARIABLE,
    cmake_script.NameKind.VARIABLE.value: sublime.KIND_VARIABLE,
}


class CompletionItem(sublime.CompletionItem):
    @classmethod
    def from_base_name(cls, name: cmake_script.BaseName):
        return cls(
            trigger=name.name, kind=KIND_MAP.get(name.kind, sublime.KIND_AMBIGUOUS)
        )


class EventListener(sublime_plugin.EventListener):
    def __init__(self):
        self._completion_result = None

    def trigger_completion(self, view: sublime.View):
        view.run_command("hide_auto_complete")
        view.run_command(
            "auto_complete",
            {
                "disable_auto_insert": True,
                "next_completion_if_showing": False,
                "auto_complete_commit_on_tab": True,
            },
        )

    def on_query_completions(
        self, view: sublime.View, prefix: Any, locations: Any
    ) -> Optional[Iterable[Any]]:
        """on query completion"""

        if not is_cmake_code(view):
            return

        if self._completion_result:
            result = self._completion_result
            self._completion_result = None
            return sublime.CompletionList(
                result,
                sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS,
            )

        thread = threading.Thread(
            target=self.get_completion_task, args=(view, locations[0])
        )
        thread.start()

    @pipe
    def get_completion_task(self, view: sublime.View, point: int):

        source = view.substr(sublime.Region(0, point))
        row, col = view.rowcol(point)
        completions = cmake_script.complete(source, row, col)

        if completions:
            self._completion_result = [
                CompletionItem.from_base_name(completion) for completion in completions
            ]

            self.trigger_completion(view)

    def on_hover(self, view: sublime.View, point: int, hover_zone: int):
        """on hover"""
        if not is_cmake_code(view):
            return

        if hover_zone == sublime.HOVER_TEXT:
            thread = threading.Thread(target=self.get_help_task, args=(view, point))
            thread.start()

    @pipe
    def get_help_task(self, view: sublime.View, point: int):
        end_point = view.word(point).b
        source = view.substr(sublime.Region(0, end_point))
        row, col = view.rowcol(end_point)
        doc = cmake_script.documentation(source, row, col)
        if doc:
            content = doc.help
            content = mistune.markdown(content)
            view.show_popup(
                content,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                max_width=1024,
            )
