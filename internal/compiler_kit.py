"""compiler kit

This module used to determine compiler path and cmake generator
"""

import os
import shutil
from dataclasses import dataclass
from io import StringIO
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
            if kit := self._get_compiler_kit(target):
                yield kit

    def _get_compiler_kit(self, compiler_target: dict) -> CompilerKit:
        c_compiler = compiler_target["c_compiler"]
        cxx_compiler = compiler_target["cxx_compiler"]

        cc_path = self._find_path(c_compiler)
        if not cc_path:
            return None

        info = self._version_info(cc_path, compiler_target["version_switch"])
        triple = self._get_triple(info)

        if triple.libc == "mingw":
            cc_path = cc_path.replace("gcc", f"{triple.triple}-gcc")

        cxx_path = cc_path.replace(c_compiler, cxx_compiler)
        generator = self._get_generator(triple)
        return CompilerKit(c_compiler, cc_path, cxx_path, generator)

    def _find_path(self, executable_name: str) -> PathStr:
        return shutil.which(executable_name, mode=os.X_OK)

    def _version_info(self, compiler_path: PathStr, version_switch: str) -> str:
        command = [compiler_path, version_switch]
        writer = StringIO()
        return_code = exec_subprocess(command, writer, captures=CaptureOption.ALL)
        if return_code != 0:
            return ""
        return writer.getvalue()

    def _get_triple(self, version_info: str) -> TargetTriple:
        return TargetTripleParser(version_info).parse()

    def _get_generator(self, triple: TargetTriple) -> GeneratorStr:
        """generator for specific target triple"""

        if self._find_path("ninja"):
            return "Ninja"
        if triple.target_os == "msys":
            return "MSYS Makefiles"
        if triple.libc == "mingw":
            return "MinGW Makefiles"
        return ""


def scan_compilers() -> List[CompilerKit]:
    """scan installed compilers"""
    scanner = CompilerKitScanner()
    return scanner.scan()
