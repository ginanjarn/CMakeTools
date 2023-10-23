import json
import os
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Iterable

import sublime
import sublime_plugin

from .api import cmake
from .api import compiler_kit as kit
from .api import sublime_settings
from .api import quickstart_generator


class OutputPanel:
    """"""

    def __init__(self):
        self.panel_name = "cmaketools"
        self.panel: sublime.View = None
        self.window: sublime.Window = None

    def create_panel(self) -> None:
        self.window = sublime.active_window()
        self.panel = self.window.create_output_panel(self.panel_name)

        settings = self.panel.settings()
        settings["gutter"] = False
        settings["auto_indent"] = False
        self.panel.set_read_only(False)

    def show(self) -> None:
        """show panel"""
        if not self.panel:
            self.create_panel()

        self.window.run_command("show_panel", {"panel": f"output.{self.panel_name}"})

    def clear(self) -> None:
        if not self.panel:
            return

        self.panel.run_command("select_all")
        self.panel.run_command("left_delete")

    def write(self, s: str) -> int:
        if not self.panel:
            self.create_panel()

        self.panel.run_command("insert", {"characters": s})
        return len(s)


def show_empty_panel(panel: OutputPanel):
    """show empty output panel"""
    panel.show()
    panel.clear()


def get_workspace_path(view: sublime.View) -> Path:
    window = view.window()
    file_name = view.file_name()

    if folders := [
        folder for folder in window.folders() if file_name.startswith(folder)
    ]:
        return Path(max(folders))
    return Path(file_name).parent


OUTPUT_PANEL = OutputPanel()


class CmaketoolsConfigureCommand(sublime_plugin.WindowCommand):
    """"""

    def run(self):
        source_path = get_workspace_path(self.window.active_view())
        build_path = source_path.joinpath("build")

        thread = threading.Thread(
            target=self.configure,
            args=(
                source_path,
                build_path,
            ),
        )
        thread.start()

    def configure(self, source_path: Path, build_path: Path = ""):
        with sublime_settings.Settings() as settings:
            build_config = settings.get("build_config", "Debug")
            c_compiler = settings.get("c_compiler", "")
            cxx_compiler = settings.get("cxx_compiler", "")
            generator = settings.get("generator", "")

        build_path = Path(source_path).joinpath("build")
        params = cmake.Configure(
            build_config, c_compiler, cxx_compiler, source_path, build_path, generator
        )
        show_empty_panel(OUTPUT_PANEL)
        cmake.exec_childprocess(params.command(), OUTPUT_PANEL)

    def is_enabled(self):
        return valid_build_source(self.window.active_view())


class CmaketoolsBuildCommand(sublime_plugin.WindowCommand):
    """"""

    build_event = threading.Event()

    def run(self, build_config: str = ""):
        source_path = get_workspace_path(self.window.active_view())
        build_path = source_path.joinpath("build")

        thread = threading.Thread(
            target=self.build,
            args=(build_path, build_config),
        )
        thread.start()

    def build(self, build_path: Path, build_config: str = ""):
        self.save_all_buffer(self.window)

        with sublime_settings.Settings() as settings:
            config = build_config or settings.get("build_config", "Debug")
            target = settings.get("build_target", "all")

        params = cmake.Build(build_path, config, target)
        show_empty_panel(OUTPUT_PANEL)
        cmake.exec_childprocess(params.command(), OUTPUT_PANEL)

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

    def run(self):
        source_path = get_workspace_path(self.window.active_view())
        build_path = source_path.joinpath("build")

        thread = threading.Thread(
            target=self.test,
            args=(build_path,),
        )
        thread.start()

    def test(self, build_path: Path):
        # build project before run 'ctest'
        CmaketoolsBuildCommand.build_event.clear()
        self.window.run_command("cmaketools_build")
        CmaketoolsBuildCommand.build_event.wait()

        with sublime_settings.Settings() as settings:
            config = settings.get("build_config", "Debug")

        params = cmake.CTest(build_path, config)
        OUTPUT_PANEL.show()
        cmake.exec_childprocess(params.command(), OUTPUT_PANEL, cwd=build_path)

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

        def on_select(index=-1):
            if index < 0:
                return
            elif index == len(kit_items):
                self.window.run_command("cmaketools_set_kits", {"scan": True})
                return

            with sublime_settings.Settings(save=True) as settings:
                settings["c_compiler"] = kit_items[index].c_compiler
                settings["cxx_compiler"] = kit_items[index].cxx_compiler

                # set generator if empty
                if not settings.get("generator"):
                    settings["generator"] = kit_items[index].generator

            # we must remove 'CMakeCache.txt' to apply changes
            self.remove_cmakecache()

        self.window.show_quick_panel(titles, on_select=on_select)

    def remove_cmakecache(self):
        source_path = get_workspace_path(self.window.active_view())
        cmake_cache = source_path.joinpath("build", "CMakeCache.txt")
        try:
            os.remove(cmake_cache)
        except FileNotFoundError:
            pass


def valid_build_source(view: sublime.View):
    return any(
        [
            view.match_selector(0, "source.cmake"),
            view.match_selector(0, "source.c++"),
            view.match_selector(0, "source.c"),
        ]
    )


def valid_source(view: sublime.View):
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
