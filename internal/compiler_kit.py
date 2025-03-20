"""compiler kit

This module used to determine compiler path and cmake generator
"""

import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterator, List

from .subprocess_helper import exec_subprocess, CaptureOption
from .triple import TargetTriple, TargetTripleParser

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


class CompilerKitScanner:
    """CompilerKit scanner"""

    def scan(self) -> List[CompilerKit]:
        return list(self._scan())

    scan_target = [
        {"c_compiler": "gcc", "cxx_compiler": "g++", "version_switch": "-v"},
        {"c_compiler": "clang", "cxx_compiler": "clang++", "version_switch": "-v"},
        {"c_compiler": "cl", "cxx_compiler": "cl", "version_switch": "/?"},
    ]

    def _scan(self) -> Iterator[CompilerKit]:

        for target in self.scan_target:
            yield from self._get_compiler_kit(target)

    def _get_compiler_kit(self, compiler_target: dict) -> Iterator[CompilerKit]:
        c_compiler = compiler_target["c_compiler"]
        cxx_compiler = compiler_target["cxx_compiler"]

        for path in self._get_paths(c_compiler):
            info = self._version_info(path, compiler_target["version_switch"])
            triple = self._get_triple(info)

            cc_path = self._get_cc_path(path, triple)
            cxx_path = cc_path.replace(c_compiler, cxx_compiler)
            generator = self._get_generator(triple)

            yield CompilerKit(c_compiler, cc_path, cxx_path, generator)

    def _get_paths(self, executable_name: str) -> List[PathStr]:
        find_cmd = "where" if os.name == "nt" else "which"
        command = [find_cmd, executable_name]

        writer = StringIO()
        return_code = exec_subprocess(command, writer, captures=CaptureOption.ALL)
        if return_code != 0:
            return []

        # Multiple executable may be available in PATH
        return writer.getvalue().splitlines()

    def _version_info(self, compiler_path: PathStr, version_switch: str) -> str:
        if not compiler_path:
            return ""

        command = [compiler_path, version_switch]

        writer = StringIO()
        return_code = exec_subprocess(command, writer, captures=CaptureOption.ALL)
        if return_code != 0:
            return ""
        return writer.getvalue()

    def _get_triple(self, version_info: str) -> TargetTriple:
        return TargetTripleParser(version_info).parse()

    def _get_cc_path(self, compiler_path: PathStr, triple: TargetTriple) -> PathStr:
        if triple.libc == "mingw":
            gcc_path = compiler_path.replace("gcc", f"{triple.triple}-gcc")
            if Path(gcc_path).is_file():
                return gcc_path

        return compiler_path

    def _get_generator(self, triple: TargetTriple) -> GeneratorStr:
        """generator for specific target triple"""

        if triple.target_os == "msys":
            return "MSYS Makefiles"

        if triple.libc == "mingw":
            return "MinGW Makefiles"

        return "NMake Makefiles" if os.name == "nt" else "Unix Makefiles"


def scan_compilers() -> List[CompilerKit]:
    """scan installed compilers"""
    scanner = CompilerKitScanner()
    return scanner.scan()
