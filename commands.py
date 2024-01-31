import json
import os
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Iterable

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

    def show(self) -> None:
        """show panel"""
        # ensure panel is created
        self.create_panel()

        self.window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

    def clear(self) -> None:
        if not self.panel:
            return

        self.panel.run_command("select_all")
        self.panel.run_command("left_delete")

    def write(self, s: str) -> int:
        # ensure panel is created
        self.create_panel()

        self.panel.run_command("insert", {"characters": s})
        return len(s)


def show_empty_panel(panel: OutputPanel):
    """show empty output panel"""
    panel.show()
    panel.clear()


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


class CmaketoolsConfigureCommand(sublime_plugin.WindowCommand):
    """"""

    def run(self):
        try:
            source_path = get_workspace_path(self.window.active_view())
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
            cmake_path = settings.get("cmake") or "cmake"
            generator = settings.get("generator")
            build_prefix = settings.get("build_prefix") or "build"
            envs = settings.get("envs")

            user_setting_variables = {
                k: v for k, v in settings.to_dict().items() if k.startswith("CMAKE_")
            }

            build_path = source_path.joinpath(build_prefix)
            cache_variables = self.omit_empty(user_setting_variables)

        params = cmake_commands.CMakeConfigureCommand(cmake_path, source_path, build_path)
        params.set_generator(generator).set_cmake_variables(cache_variables)

        show_empty_panel(OUTPUT_PANEL)
        cmake_commands.exec_childprocess(params.command(), OUTPUT_PANEL, env=envs)

    def is_enabled(self):
        return valid_build_source(self.window.active_view())


class CmaketoolsBuildCommand(sublime_plugin.WindowCommand):
    """"""

    build_event = threading.Event()

    def run(self, config: str = "", target: str = ""):
        try:
            source_path = get_workspace_path(self.window.active_view())
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.build,
            args=(source_path, config, target),
        )
        thread.start()

    def build(self, source_path: Path, config: str = "", target: str = ""):
        self.save_all_buffer(self.window)

        with sublime_settings.Settings() as settings:
            cmake_path = settings.get("cmake") or "cmake"
            build_prefix = settings.get("build_prefix") or "build"
            njobs = settings.get("jobs") or 4
            envs = settings.get("envs")

            build_path = source_path.joinpath(build_prefix)

        params = cmake_commands.CMakeBuildCommand(cmake_path, build_path)
        params.set_config(config).set_target(target).set_parallel_jobs(njobs)

        show_empty_panel(OUTPUT_PANEL)
        cmake_commands.exec_childprocess(params.command(), OUTPUT_PANEL, env=envs)

        self.build_event.set()

    def save_all_buffer(self, window: sublime.Window):
        unsaved_views = [view for view in window.views() if view.is_dirty()]
        if not unsaved_views:
            return

        message = f"{len(unsaved_views)} unsaved document(s).\n\nSave all?"
        save_all = sublime.ok_cancel_dialog(message, title="Build Warning !")
        if save_all:
            for view in unsaved_views:
                view.run_command("save", {"async": False})

    def is_enabled(self):
        return valid_build_source(self.window.active_view())


class CmaketoolsTestCommand(sublime_plugin.WindowCommand):
    """"""

    def run(self, config: str = "", target: str = "test"):
        try:
            source_path = get_workspace_path(self.window.active_view())
        except Exception as err:
            show_workspace_error(err)
            return

        thread = threading.Thread(
            target=self.test,
            args=(source_path, config, target),
        )
        thread.start()

    def test(self, source_path: Path, config: str = "", target: str = ""):
        # build project before run 'ctest'
        CmaketoolsBuildCommand.build_event.clear()
        self.window.run_command("cmaketools_build")
        CmaketoolsBuildCommand.build_event.wait()

        with sublime_settings.Settings() as settings:
            ctest_path = settings.get("ctest") or "ctest"
            build_prefix = settings.get("build_prefix") or "build"
            njobs = settings.get("jobs") or 4

            build_path = source_path.joinpath(build_prefix)

        params = cmake_commands.CTestCommand(ctest_path, build_path)
        params.set_config(config).set_target(target).set_parallel_jobs(njobs)

        print(params.command())

        OUTPUT_PANEL.show()
        cmake_commands.exec_childprocess(params.command(), OUTPUT_PANEL, cwd=build_path)

    def is_enabled(self):
        return valid_build_source(self.window.active_view())


class KitManager:
    """"""

    def scan(self) -> Iterator[kit.CompilerKit]:
        scanner = kit.Scanner()
        yield from scanner.scan()

    cache_path = Path(__file__).parent.joinpath("var", "compiler_kits.json")

    def load_cache(self) -> Iterator[kit.CompilerKit]:
        if not self.cache_path.is_file():
            return

        jstring = self.cache_path.read_text()
        data = json.loads(jstring)
        for item in data:
            yield kit.CompilerKit(
                name=item["name"],
                c_compiler=item["c_compiler"],
                cxx_compiler=item["cxx_compiler"],
                generator=item["generator"],
            )

    def save_cache(self, kits: Iterable[kit.CompilerKit]) -> None:
        cache_dir = self.cache_path.parent
        if not cache_dir.is_dir():
            cache_dir.mkdir(parents=True)

        data = [asdict(item) for item in kits]
        jstring = json.dumps(data, indent=2)
        self.cache_path.write_text(jstring)


class CmaketoolsSetKitsCommand(sublime_plugin.WindowCommand, KitManager):
    """"""

    def run(self, scan: bool = False):
        thread = threading.Thread(target=self._run, args=(scan,))
        thread.start()

    def _run(self, scan: bool = False):
        try:
            kit_items = list(self.load_cache())
        except Exception:
            # force scan if exception
            scan = True

        if scan or (not kit_items):
            sublime.status_message("Scanning compilers...")
            kit_items = list(self.scan())
            sublime.status_message(f"{len(kit_items)} kits found.")

            self.save_cache(kit_items)

        titles = [f"[{item.name.upper()}] {item.c_compiler}" for item in kit_items]
        titles.append("Scan kits...")

        def to_posix_path(path: str) -> str:
            return Path(path).as_posix()

        def on_select(index=-1):
            if index < 0:
                return
            elif index == len(kit_items):
                self.window.run_command("cmaketools_set_kits", {"scan": True})
                return

            with sublime_settings.Settings(save=True) as settings:
                # cmake error on forward slash('\') separated path
                settings.set(
                    "CMAKE_C_COMPILER", to_posix_path(kit_items[index].c_compiler)
                )
                settings.set(
                    "CMAKE_CXX_COMPILER", to_posix_path(kit_items[index].cxx_compiler)
                )

                # set generator if empty
                if not settings.get("generator"):
                    settings.set("generator", kit_items[index].generator)

            # we must remove 'CMakeCache.txt' to apply changes
            self.remove_cmakecache()

        self.window.show_quick_panel(titles, on_select=on_select)

    def remove_cmakecache(self):
        try:
            source_path = get_workspace_path(self.window.active_view())
            cmake_cache = source_path.joinpath("build", "CMakeCache.txt")
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

        self.view.window().run_command("cmaketools_set_kits", {"scan": True})

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
