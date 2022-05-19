"""CMaketools main implementation"""

import logging
import os
import re
import threading
from dataclasses import dataclass

import sublime
import sublime_plugin

from .api import build_generator

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)  # module logging level
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


def progress(title: str):
    def wraps(func):
        def wrapper(*args, **kwargs):
            return func(args, kwargs)

        return wrapper

    try:
        view: sublime.View = sublime.active_window().active_view()
        view.set_status("CMAKE_PROGRESS", f"CMake Tools: {title}")
        return wraps
    finally:
        view.erase_status("CMAKE_PROGRESS")


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
                result = build_generator.build(
                    self.project.path, self.project.build_mode
                )
            except Exception as err:
                LOGGER.error(f"build error --> {err}")
            else:
                print(result)
            finally:
                LOGGER.debug("finish build")

        thread = threading.Thread(target=build)
        thread.start()
