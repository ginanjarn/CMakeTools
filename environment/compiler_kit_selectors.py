import os
import shutil
import threading
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterator, List, Optional

import sublime
import sublime_plugin

from .triple import TargetTriple, TargetTripleParser
from ..utils import sublime_settings
from ..utils.workspace import get_workspace_path
from ..utils.child_process import run, CaptureOption

PathStr = str
GeneratorStr = str


@dataclass
class CompilerKit:
    """CompilerKit data

    c_compiler: c compiler path
    cxx_compiler: cxx_compiler compiler path
    generator: prefered generator
    """

    name: str
    c_compiler: PathStr
    cxx_compiler: PathStr
    generator: GeneratorStr


class KitScanner:
    """CompilerKit scanner"""

    def __init__(self, search_path: Optional[str] = None) -> None:
        self.search_path = search_path

    def scan(self) -> List[CompilerKit]:
        return list(self._scan())

    scan_target = [
        {"c_compiler": "gcc", "cxx_compiler": "g++", "version_switch": "-v"},
        {"c_compiler": "clang", "cxx_compiler": "clang++", "version_switch": "-v"},
        {"c_compiler": "cl", "cxx_compiler": "cl", "version_switch": "/?"},
    ]

    def _scan(self) -> Iterator[CompilerKit]:
        for target in self.scan_target:
            if kit := self._get_compiler_kit(target):
                yield kit

    def _get_compiler_kit(self, compiler_target: dict) -> CompilerKit:
        c_compiler = compiler_target["c_compiler"]
        cxx_compiler = compiler_target["cxx_compiler"]

        cc_path = self._find_executable_path(c_compiler)
        if not cc_path:
            return None

        info = self._version_info(cc_path, compiler_target["version_switch"])
        triple = self._get_triple(info)

        # resolve mingw gcc target executable
        if triple.libc == "mingw":
            cc_path = cc_path.replace("gcc", f"{triple.triple}-gcc")

        cxx_path = cc_path.replace(c_compiler, cxx_compiler)
        generator = self._get_generator(triple)
        return CompilerKit(c_compiler, cc_path, cxx_path, generator)

    def _find_executable_path(self, name: str) -> PathStr:
        return shutil.which(name, mode=os.X_OK, path=self.search_path)

    def _version_info(self, compiler_path: PathStr, version_switch: str) -> str:
        command = [compiler_path, version_switch]
        writer = StringIO()
        return_code = run(command, writer, captures=CaptureOption.ALL)
        if return_code != 0:
            return ""
        return writer.getvalue()

    def _get_triple(self, version_info: str) -> TargetTriple:
        return TargetTripleParser(version_info).parse()

    def _get_generator(self, triple: TargetTriple) -> GeneratorStr:
        """generator for specific target triple"""

        if self._find_executable_path("ninja"):
            return "Ninja"
        if triple.target_os == "msys":
            return "MSYS Makefiles"
        if triple.libc == "mingw":
            return "MinGW Makefiles"
        return ""


def scan_kits(search_path: Optional[str]) -> List[CompilerKit]:
    """scan installed compiler kits"""
    scanner = KitScanner(search_path)
    return scanner.scan()


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

        with sublime_settings.Settings() as settings:
            try:
                search_path = settings.get("envs")["PATH"]
            except Exception:
                search_path = None

        kit_items = scan_kits(search_path)
        sublime.status_message(f"{len(kit_items)} kits found.")

        titles = [f"[{item.name.upper()}] {item.c_compiler}" for item in kit_items]

        def on_select(index=-1):
            if index < 0:
                return

            item = kit_items[index]

            with sublime_settings.Settings(save=True) as settings:

                cache_variables_key = "cacheVariables"
                cache_variables = settings.get(cache_variables_key, {})
                cache_variables.update(
                    {
                        # cmake error on forward slash('\') separated path
                        "CMAKE_C_COMPILER": Path(item.c_compiler).as_posix(),
                        "CMAKE_CXX_COMPILER": Path(item.cxx_compiler).as_posix(),
                    }
                )
                settings.set(cache_variables_key, cache_variables)

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

        except Exception:
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
