import threading
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import sublime
import sublime_plugin

from .internal import cmake_commands
from .internal import sublime_settings
from .internal.workspace import get_workspace_path
from .internal.panels import OutputPanel


def valid_build_source(view: sublime.View):
    if not view:
        return False
    return view.match_selector(0, "source.cmake,source.c++,source.c")


OUTPUT_PANEL = OutputPanel()


def show_workspace_error(error: Exception):
    message = f"Unable find project!\n\nError: {error} in projects."
    sublime.error_message(message)


def omit_empty(mapping: dict) -> dict:
    """"""
    return {k: v for k, v in mapping.items() if v}


def is_cmakepresets_exists(project_path: Path) -> bool:
    return (
        Path(project_path, "CMakePresets.json").is_file()
        or Path(project_path, "CMakeUserPresets.json").is_file()
    )


class CmaketoolsConfigureCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        try:
            project_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(target=self.configure, args=(project_path,))
        thread.start()

    def configure(self, project_path: Path):
        with sublime_settings.Settings() as settings:
            generator = settings.get("generator")
            build_prefix = settings.get("build_prefix") or "build"
            envs = settings.get("envs")
            cache_variables = settings.get("cacheVariables", {})
            preset = settings.get("preset") or "default"

        use_presets = is_cmakepresets_exists(project_path)
        if use_presets:
            params = cmake_commands.PresetParams(preset)
        else:
            params = cmake_commands.ConfigureParams(
                generator, omit_empty(cache_variables)
            )

        OUTPUT_PANEL.show(clear=True)
        project = cmake_commands.Project(
            project_path,
            OUTPUT_PANEL,
            build_prefix=build_prefix,
            environment=envs,
            use_presets=use_presets,
        )
        project.configure(params)

    def is_enabled(self):
        return valid_build_source(self.view)


class CmaketoolsBuildCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit, target: str):
        try:
            project_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.build,
            args=(project_path, target),
        )
        thread.start()

    def build(self, project_path: Path, target: str):
        # cancel if target not assigned
        if not target:
            return

        window = self.view.window()
        if not self.continue_unsaved_window(window):
            return

        with sublime_settings.Settings() as settings:
            build_prefix = settings.get("build_prefix") or "build"
            envs = settings.get("envs")
            preset = settings.get("preset") or "default"

        use_presets = is_cmakepresets_exists(project_path)
        if use_presets:
            params = cmake_commands.PresetParams(preset)
        else:
            params = cmake_commands.BuildParams(target)

        OUTPUT_PANEL.show()
        project = cmake_commands.Project(
            project_path,
            OUTPUT_PANEL,
            build_prefix=build_prefix,
            environment=envs,
            use_presets=use_presets,
        )
        project.build(params, "--")

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
            project_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.test,
            args=(project_path, test_regex),
        )
        thread.start()

    def test(self, project_path: Path, test_regex: str):

        with sublime_settings.Settings() as settings:
            build_prefix = settings.get("build_prefix") or "build"
            envs = settings.get("envs")
            preset = settings.get("preset") or "default"

        use_presets = is_cmakepresets_exists(project_path)
        if use_presets:
            params = cmake_commands.PresetParams(preset)
        else:
            params = cmake_commands.TestParams(test_regex)

        OUTPUT_PANEL.show()
        project = cmake_commands.Project(
            project_path,
            OUTPUT_PANEL,
            build_prefix=build_prefix,
            environment=envs,
            use_presets=use_presets,
        )
        project.test(params)

    def is_enabled(self):
        return valid_build_source(self.view)


@dataclass
class TargetMap:
    lineno: int
    target: str


class CmakeBuildTargetInFileCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        targets = ["all"] + list(self.scan_target())

        def on_select(index):
            if index > -1:
                self.view.run_command("cmaketools_build", {"target": targets[index]})

        # select the target if only one found
        if len(targets) == 2:
            on_select(index=1)
            return

        self.view.window().show_quick_panel(targets, on_select=on_select)

    # cmake add target with 'add_library()' and 'add_executable()' command
    pattern = re.compile(r"(?:qt_)?add_(?:library|executable)\s*\(\s*([\w\-]+)")

    def scan_target(self) -> Iterator[str]:
        for region in self.view.find_by_selector("entity.name.function"):
            name = self.view.substr(region)
            if name not in {"add_library", "add_executable", "qt_add_executable"}:
                continue

            line_str = self.view.substr(self.view.line(region))
            if match := self.pattern.match(line_str.lstrip()):
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


class CmakeTestTargetInFileCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        targets = ["all"] + list(self.scan_target())

        def on_select(index):
            if index > -1:
                target = targets[index] if index > 0 else ""
                self.view.run_command("cmaketools_test", {"test_regex": target})

        # select the target if only one found
        if len(targets) == 2:
            on_select(index=1)
            return

        self.view.window().show_quick_panel(targets, on_select=on_select)

    # cmake add target with 'add_test()' command
    pattern = re.compile(r"add_test\s*\(\s*\s*NAME\s+([\w\-:]+)\s")

    def scan_target(self) -> Iterator[str]:
        for region in self.view.find_by_selector("entity.name.function"):
            name = self.view.substr(region)
            if name != "add_test":
                continue

            line_str = self.view.substr(self.view.line(region))
            if match := self.pattern.match(line_str.lstrip()):
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


class CmakeRunScriptCommand(sublime_plugin.TextCommand):
    """"""

    def run(self, edit: sublime.Edit):
        if self.view.is_dirty():
            message = (
                f"{Path(self.view.file_name()).name!r} is unsaved.\n"
                "\n"
                "Save now and run?"
            )
            save_document = sublime.ok_cancel_dialog(
                message, ok_title="Save", title="Document Unsaved!"
            )
            if not save_document:
                # cancel run unsaved document
                return

            self.view.run_command("save")

        try:
            project_path = get_workspace_path(self.view)
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.run_script,
            args=(project_path, self.view.file_name()),
        )
        thread.start()

    def run_script(self, project_path: Path, file_path: str):
        with sublime_settings.Settings() as settings:
            envs = settings.get("envs")

        OUTPUT_PANEL.show()
        params = cmake_commands.ScriptParams(file_path)
        project = cmake_commands.Project(project_path, OUTPUT_PANEL, environment=envs)
        project.run_script(params)

    def is_visible(self) -> bool:
        if file_name := self.view.file_name():
            return Path(file_name).suffix == ".cmake"
        return False


class CmaketoolsSaveEventListener(sublime_plugin.EventListener):
    """"""

    def on_post_save_async(self, view: sublime.View):
        if not view.match_selector(0, "source.cmake"):
            return

        if Path(view.file_name()).name != "CMakeLists.txt":
            return

        with sublime_settings.Settings() as settings:
            if settings.get("configure_on_save", False):
                view.window().run_command("cmaketools_configure")
