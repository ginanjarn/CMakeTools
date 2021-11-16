"""cmake tools"""

import os
import threading

import sublime
import sublime_plugin

from .plugins import commands


def get_project(view: sublime.View):
    window = view.window()
    # window:sublime.Window = window
    file_name = view.file_name()
    if not file_name:
        raise ValueError("unable get file_name")
    folders = window.folders()
    try:
        project_path = max(folder for folder in folders if file_name.startswith(folder))
    except ValueError:
        project_path = os.path.dirname(file_name)
    return project_path


CMAKE_BUILD_GENERATOR = [
    "auto",
    "NMake Makefiles",
    "MSYS Makefiles",
    "MinGW Makefiles",
    "Unix Makefiles",
    "Ninja",
    "Ninja Multi-Config",
]

CMAKE_PROJECT_TYPES = ["executable", "library"]


# bootstrap CMakeLists.txt
class CmakeBootstrapCommand(sublime_plugin.TextCommand):
    def __init__(self, view: sublime.View):
        self.view = view
        self.window = self.view.window()

        self.project_types = ("executable", "library")
        self.window_folders = []

        self.project_name = ""
        self.project_path = ""
        self.project_type = ""
        self.project_version = "0.1.0"

    def run(self, edit: sublime.Edit):

        # # 1
        # self.project_path = get_project(self.view)
        # # 2
        # self.get_project_name()

        # 1
        self.get_project_path()

    def get_project_path(self):
        self.window_folders = self.window.folders()

        if not self.window_folders:
            initial_text = ""
            file_name = self.view.file_name()
            if file_name:
                initial_text = os.path.dirname(file_name)
            # input path manually
            self.window.show_input_panel(
                "project path",
                initial_text=initial_text,
                on_done=self.on_input_projectpath_done,
                on_change=None,
                on_cancel=None,
            )
        else:
            self.window.show_quick_panel(
                self.window_folders,
                on_select=self.on_select_project_path,
                flags=sublime.MONOSPACE_FONT,
            )

    def on_input_projectpath_done(self, text):
        if os.path.exists(text):
            self.project_path = text
        # 2
        self.get_project_name()

    def on_select_project_path(self, index):
        if index < 0:
            return
        self.project_path = self.window_folders[index]

        # 2
        self.get_project_name()

    def get_project_name(self):
        self.window.show_input_panel(
            "project name",
            initial_text="awesomeproject",
            on_done=self.on_input_projectname_done,
            on_change=None,
            on_cancel=None,
        )

    def on_input_projectname_done(self, text):
        if not text:
            return

        self.project_name = text

        # 3
        self.get_project_type()

    def get_project_type(self):
        self.window.show_quick_panel(
            CMAKE_PROJECT_TYPES,
            on_select=self.on_select_project_type,
            flags=sublime.MONOSPACE_FONT,
        )

    def on_select_project_type(self, index):
        if index < 0:
            return
        self.project_type = CMAKE_PROJECT_TYPES[index]

        # 4
        self.get_project_version()

    def get_project_version(self):
        self.window.show_input_panel(
            "project version",
            initial_text="0.1.0",
            on_done=self.on_input_projectversion_done,
            on_change=None,
            on_cancel=None,
        )

    def on_input_projectversion_done(self, text):
        if not text:
            return

        self.project_version = text

        # 5
        self.create_bootstrap()

    def create_bootstrap(self):
        print(
            self.project_path,
            self.project_name,
            self.project_type,
            self.project_version,
        )
        thread = threading.Thread(target=self.create_bootstrap_task)
        thread.start()

    def create_bootstrap_task(self):
        try:
            commands.bootstrap_cmakelist(
                project_path=self.project_path,
                project_name=self.project_name,
                project_type=self.project_type,
                project_version=self.project_version,
            )

        except Exception as err:
            print(repr(err))
            sublime.error_message("Bootrapping CMakeLists.txt failed!")


# exec cmake
class CmakeGenerate(sublime_plugin.TextCommand):
    def __init__(self, view):
        self.view = view
        self.window = self.view.window()

        self.project_path = ""
        self.cmake_path = ""
        self.compilers = []
        self.c_compiler = ""
        self.cmake_build_generator = ""

    def run(self, edit):
        thread = threading.Thread(target=self.run_task)
        thread.run()

    def run_task(self):
        # 1
        self.project_path = get_project(self.view)
        # 2
        self.get_c_compiler()

    def get_c_compiler(self):
        self.compilers = commands.get_compiler_list()

        self.window.show_quick_panel(
            self.compilers,
            on_select=self.on_select_compiler,
            flags=sublime.MONOSPACE_FONT,
        )

    def on_select_compiler(self, index):
        if index < 0:
            return
        self.c_compiler = self.compilers[index]

        # 3
        self.get_build_generator()

    def get_build_generator(self):
        self.window.show_quick_panel(
            CMAKE_BUILD_GENERATOR,
            on_select=self.on_select_build_generator,
            flags=sublime.MONOSPACE_FONT,
        )

    def on_select_build_generator(self, index):
        if index < 0:
            return

        if index > 1:
            self.cmake_build_generator = CMAKE_BUILD_GENERATOR[index]

        # 4
        self.exec_cmake()

    def exec_cmake(self):
        print(
            self.project_path,
            self.cmake_path,
            self.c_compiler,
            self.cmake_build_generator,
        )
        thread = threading.Thread(target=self.exec_cmake_task)
        thread.start()

    def exec_cmake_task(self):
        try:
            if not self.cmake_path:
                self.cmake_path = commands.cmake_path()

            commands.generate_cmake(
                self.project_path,
                cmake_path=self.cmake_path,
                c_compiler=self.c_compiler,
                build_generator=self.cmake_build_generator,
            )

        except Exception as err:
            print(err)
            sublime.error_message("CMake Generate build failed!")

        else:
            sublime.message_dialog("CMake Generate build success!")
