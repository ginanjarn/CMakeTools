"""compiler kit

This module used to determine compiler path and cmake generator
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List

from .triple import (
    TargetTriple,
    find_target_triple,
    parse_target_triple,
)

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


def scan_compilers() -> List[CompilerKit]:
    """scan installed compilers"""
    scanner = Scanner()
    return scanner.scan()


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


def exec_subprocess(command: List[str]) -> str:
    """get subprocess then return the output from stdout and stderr"""

    proc = subprocess.Popen(
        command,
        # stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        startupinfo=STARTUPINFO,
    )

    sout, _ = proc.communicate()
    if proc.returncode == 0:
        return sout.decode()

    return ""


class Scanner:
    """CompilerKit scanner"""

    compiler_switch = [
        {"cc_name": "gcc", "cxx_name": "g++", "version_switch": "-v"},
        {"cc_name": "clang", "cxx_name": "clang++", "version_switch": "-v"},
        {"cc_name": "cl", "cxx_name": "cl", "version_switch": "/?"},
    ]

    def _get_paths(self, executable_name: str) -> List[PathStr]:
        find_cmd = "where" if os.name == "nt" else "which"
        command = [find_cmd, executable_name]
        # Multiple executable may be detected.
        return exec_subprocess(command).splitlines()

    def _version_info(self, compiler_path: PathStr, version_switch: str) -> str:
        if not compiler_path:
            return ""

        command = [compiler_path, version_switch]
        return exec_subprocess(command)

    def _get_triple(self, version_info: str) -> TargetTriple:
        return parse_target_triple(find_target_triple(version_info))

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

    def _scan(self) -> Iterator[CompilerKit]:
        def get_compiler(target) -> Iterator[CompilerKit]:
            cc_name = target["cc_name"]
            cxx_name = target["cxx_name"]

            for path in self._get_paths(cc_name):
                info = self._version_info(path, target["version_switch"])
                triple = self._get_triple(info)

                cc_path = self._get_cc_path(path, triple)
                cxx_path = cc_path.replace(cc_name, cxx_name)
                generator = self._get_generator(triple)

                yield CompilerKit(cc_name, cc_path, cxx_path, generator)

        for target in self.compiler_switch:
            yield from get_compiler(target)

    def scan(self) -> List[CompilerKit]:
        return list(self._scan())
