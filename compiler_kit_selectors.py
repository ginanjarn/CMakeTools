import os
import sublime
import sublime_plugin
import threading
from pathlib import Path

from .internal import compiler_kit as kit
from .internal import sublime_settings
from .internal.workspace import get_workspace_path


def valid_build_source(view: sublime.View):
    if not view:
        return False
    return view.match_selector(0, "source.cmake,source.c++,source.c")


def valid_source(view: sublime.View):
    return view.match_selector(0, "source.cmake")


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
