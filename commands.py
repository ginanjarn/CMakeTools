import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import sublime
import sublime_plugin

from .api import cmake_commands
from .api import compiler_kit as kit
from .api import sublime_settings
from .api import quickstart_generator


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
        point = self.panel.size() if point < 0 else point

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
        # ensure panel is created
        self.create_panel()
        point = self.panel.size()
        # move cursor to the end
        self.move_cursor(point)

        self.panel.show(point, keep_to_left=True)

        self.panel.run_command("insert", {"characters": s})
        return len(s)


def get_workspace_path(view: sublime.View) -> Path:
    """get workspace path
    Use directory contain 'CMakeLists.txt' as workspace path.

    Raise FileNotFoundError if not found.
    """

    file_name = view.file_name()
    folders = [
        folder for folder in view.window().folders() if file_name.startswith(folder)
    ]

    # sort form shortest path
    folders.sort()
    # set first folder contain 'CMakeLists.txt' as workspace path
    for folder in folders:
        if (path := Path(folder).joinpath("CMakeLists.txt")) and path.is_file():
            return path.parent

    raise FileNotFoundError("unable find 'CMakeLists.txt'")


OUTPUT_PANEL = OutputPanel()


def show_workspace_error(error: Exception):
    message = f"Unable find project!\n\nError: {error} in projects."
    sublime.error_message(message)


class CmaketoolsConfigureCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        try:
            source_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(target=self.configure, args=(source_path,))
        thread.start()

    @staticmethod
    def omit_empty(mapping: dict) -> dict:
        return {k: v for k, v in mapping.items() if v}

    def configure(self, source_path: Path):
        with sublime_settings.Settings() as settings:
            generator = settings.get("generator")
            build_prefix = settings.get("build_prefix") or "build"
            envs = settings.get("envs")

            user_cache_entries = {
                k: v for k, v in settings.to_dict().items() if k.startswith("CMAKE_")
            }

            build_path = source_path.joinpath(build_prefix)
            cache_entries = self.omit_empty(user_cache_entries)

        command = cmake_commands.CMakeCommands.configure(
            source_path, build_path, cache_entry=cache_entries, generator=generator
        )

        OUTPUT_PANEL.show(clear=True)
        ret = cmake_commands.exec_subprocess(
            command, OUTPUT_PANEL, env=envs, cwd=source_path
        )
        print(f"process terminated with exit code {ret}")

    def is_enabled(self):
        return valid_build_source(self.view)


class CmaketoolsBuildCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, target: str):
        try:
            source_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.build,
            args=(source_path, target),
        )
        thread.start()

    def build(self, source_path: Path, target: str):
        # cancel if target not assigned
        if not target:
            return

        window = self.view.window()
        if not self.continue_unsaved_window(window):
            return

        with sublime_settings.Settings() as settings:
            build_prefix = settings.get("build_prefix") or "build"
            build_path = source_path.joinpath(build_prefix)

            njobs = settings.get("jobs") or -1
            envs = settings.get("envs")

        command = cmake_commands.CMakeCommands.build(
            build_path, target=target, njobs=njobs
        )

        OUTPUT_PANEL.show()
        ret = cmake_commands.exec_subprocess(
            command, OUTPUT_PANEL, cwd=build_path, env=envs
        )
        print(f"process terminated with exit code {ret}")

    def continue_unsaved_window(self, window: sublime.Window) -> bool:
        unsaved_views = [view for view in window.views() if view.is_dirty()]
        if not unsaved_views:
            return True

        message = f"{len(unsaved_views)} unsaved document(s).\n\nSave all?"
        result = sublime.yes_no_cancel_dialog(
            message, title="Build Warning !", yes_title="Save All"
        )

        # cancel
        if result == sublime.DialogResult.CANCEL:
            return False

        if result == sublime.DialogResult.YES:
            window.run_command("save_all")

        return True

    def is_enabled(self):
        return valid_build_source(self.view)


class CmaketoolsTestCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, test_regex: str = ""):
        try:
            source_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.test,
            args=(source_path, test_regex),
        )
        thread.start()

    def test(self, source_path: Path, test_regex: str):

        with sublime_settings.Settings() as settings:
            build_prefix = settings.get("build_prefix") or "build"
            build_path = source_path.joinpath(build_prefix)
            njobs = settings.get("jobs") or -1

        command = cmake_commands.CTestCommand(
            build_path, test_regex=test_regex, njobs=njobs
        )

        OUTPUT_PANEL.show()
        ret = cmake_commands.exec_subprocess(command, OUTPUT_PANEL, cwd=build_path)
        print(f"process terminated with exit code {ret}")

    def is_enabled(self):
        return valid_build_source(self.view)


@dataclass
class TargetMap:
    lineno: int
    target: str


class CmakeBuildTargetOnFileCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        source = self.view.substr(sublime.Region(0, self.view.size()))
        targets = ["all"] + list(self.scan_target(source))

        def on_select(index):
            if index > -1:
                self.view.run_command("cmaketools_build", {"target": targets[index]})

        self.view.window().show_quick_panel(targets, on_select=on_select)

    # cmake add target with 'add_library()' and 'add_executable()' command
    pattern = re.compile(r"add_(?:library|executable)\s*\(\s*([\w\-:]+)\s")

    def scan_target(self, text: str) -> Iterator[str]:
        for line in text.splitlines():
            if match := self.pattern.match(line.strip()):
                yield match.group(1)

    def is_visible(self, event: Optional[dict] = None) -> bool:
        return (not self.view.is_dirty()) and self.view.match_selector(
            0, "source.cmake"
        )


class CmakeBuildHoveredTargetCommand(sublime_plugin.TextCommand):
    """"""

    # cmake add target with 'add_library()' and 'add_executable()' command
    pattern = re.compile(r"add_(?:library|executable)\s*\(\s*([\w\-:]+)\s")

    def run(self, edit: sublime.Edit, event: dict):
        line_text = self.view.substr(self.view.line(event["text_point"]))
        if match := self.pattern.match(line_text.strip()):
            self.view.run_command("cmaketools_build", {"target": match.group(1)})

    def is_visible(self, event: dict) -> bool:
        if self.view.is_dirty() or (not self.view.match_selector(0, "source.cmake")):
            return False

        line_text = self.view.substr(self.view.line(event["text_point"]))
        match = self.pattern.match(line_text.strip())
        return bool(match)

    def want_event(self) -> bool:
        return True


class CmakeTestTargetOnFileCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        source = self.view.substr(sublime.Region(0, self.view.size()))
        targets = ["all"] + list(self.scan_target(source))

        def on_select(index):
            if index > -1:
                target = targets[index] if index > 0 else ""
                self.view.run_command("cmaketools_test", {"test_regex": target})

        self.view.window().show_quick_panel(targets, on_select=on_select)

    # cmake add target with 'add_test()' command
    pattern = re.compile(r"add_test\s*\(\s*\s*NAME\s+([\w\-:]+)\s")

    def scan_target(self, text: str) -> Iterator[str]:
        for line in text.splitlines():
            if match := self.pattern.match(line.strip()):
                yield match.group(1)

    def is_visible(self) -> bool:
        return (not self.view.is_dirty()) and self.view.match_selector(
            0, "source.cmake"
        )


class CmakeTestHoveredTargetCommand(sublime_plugin.TextCommand):
    """"""

    # cmake add target with 'add_test()' command
    pattern = re.compile(r"add_test\s*\(\s*\s*NAME\s+([\w\-:]+)\s")

    def run(self, edit: sublime.Edit, event: dict):
        line_text = self.view.substr(self.view.line(event["text_point"]))
        if match := self.pattern.match(line_text.strip()):
            self.view.run_command("cmaketools_test", {"test_regex": match.group(1)})

    def is_visible(self, event: dict) -> bool:
        if self.view.is_dirty() or (not self.view.match_selector(0, "source.cmake")):
            return False

        line_text = self.view.substr(self.view.line(event["text_point"]))
        match = self.pattern.match(line_text.strip())
        return bool(match)

    def want_event(self) -> bool:
        return True


class CmaketoolsSetKitsCommand(sublime_plugin.WindowCommand):
    """"""

    def run(self):
        thread = threading.Thread(target=self._set_task)
        thread.start()

    def _set_task(self):
        sublime.status_message("Scanning compilers...")
        kit_items = kit.scan_compilers()
        sublime.status_message(f"{len(kit_items)} kits found.")

        titles = [f"[{item.name.upper()}] {item.c_compiler}" for item in kit_items]

        def on_select(index=-1):
            if index < 0:
                return

            item = kit_items[index]

            with sublime_settings.Settings(save=True) as settings:
                # cmake error on forward slash('\') separated path
                settings.set("CMAKE_C_COMPILER", Path(item.c_compiler).as_posix())
                settings.set("CMAKE_CXX_COMPILER", Path(item.cxx_compiler).as_posix())

                # set generator if empty
                if not settings.get("generator"):
                    settings.set("generator", item.generator)

            # we must remove 'CMakeCache.txt' to apply changes
            self.remove_cmakecache()

        self.window.show_quick_panel(titles, on_select=on_select)

    def remove_cmakecache(self):
        try:
            with sublime_settings.Settings() as settings:
                prefix = settings.get("build_prefix") or "build"

            source_path = get_workspace_path(self.window.active_view())
            cmake_cache = source_path.joinpath(prefix, "CMakeCache.txt")
            os.remove(cmake_cache)

        except FileNotFoundError:
            pass


def valid_build_source(view: sublime.View):
    if not view:
        return False
    return view.match_selector(0, "source.cmake,source.c++,source.c")


def valid_source(view: sublime.View):
    if not view:
        return False
    return view.match_selector(0, "source.cmake")


class CmaketoolsKitScanEvent(sublime_plugin.ViewEventListener):
    """"""

    def on_activate_async(self):
        if not valid_build_source(self.view):
            return

        # set kit if not configured
        with sublime_settings.Settings(save=True) as settings:
            if all(
                [
                    settings.get("c_compiler"),
                    settings.get("cxx_compiler"),
                    settings.get("generator"),
                ]
            ):
                return

        self.view.window().run_command("cmaketools_set_kits")

    def on_post_save_async(self):
        if not valid_source(self.view):
            return

        # set kit if not configured
        with sublime_settings.Settings() as settings:
            if settings.get("configure_on_save", False):
                self.view.window().run_command("cmaketools_configure")


class CmaketoolsQuickstartCommand(sublime_plugin.WindowCommand):
    def run(self):
        thread = threading.Thread(target=self._run)
        thread.start()

    def _run(self):
        folders = self.window.folders()
        project_types = quickstart_generator.PROJECT_TYPES

        workspace_path = ""
        project_type = ""

        def on_done_input(value: str):
            project_name = value

            quickstart_generator.generate_quickstart(
                workspace_path, project_type, project_name
            )

        def on_select_type(index=-1):
            if index < 0:
                return

            nonlocal project_type
            project_type = project_types[index]
            self.window.show_input_panel(
                "Project Name:",
                Path(workspace_path).name,
                on_done=on_done_input,
                on_change=None,
                on_cancel=None,
            )

        def on_select_folder(index=-1):
            if index < 0:
                return

            nonlocal workspace_path
            workspace_path = folders[index]

            self.window.show_quick_panel(
                project_types,
                on_select=on_select_type,
                placeholder="Project Type",
            )

        self.window.show_quick_panel(
            folders,
            on_select=on_select_folder,
            placeholder="Project Location",
        )
