"""compiler kit

This module used to determine compiler path and cmake generator
"""

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

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


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


def get_subprocess_result(command: str) -> str:
    """get subprocess then return the output from stdout and stderr"""

    proc = subprocess.run(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        startupinfo=STARTUPINFO,
    )
    result = proc.stdout.strip().decode()

    if proc.returncode == 0:
        return result

    return ""


class Scanner:
    """CompilerKit scanner"""

    scan_compilers = [
        {"cc_name": "gcc", "cxx_name": "g++", "version_switch": "-v"},
        {"cc_name": "clang", "cxx_name": "clang++", "version_switch": "-v"},
        {"cc_name": "cl", "cxx_name": "cl", "version_switch": "/?"},
    ]

    def _get_path(self, cc_name: str) -> PathStr:
        find_cmd = "where" if os.name == "nt" else "which"
        command = f"{find_cmd} {cc_name}"
        return get_subprocess_result(command)

    def _get_info(self, compiler_path: PathStr, version_switch: str) -> str:
        if not compiler_path:
            return ""

        command = f"{compiler_path!r} {version_switch}"
        return get_subprocess_result(command)

    def _get_triple(self, version_info: str) -> TargetTriple:
        return parse_target_triple(find_target_triple(version_info))

    def _get_cc_path(self, compiler_path: PathStr, triple: TargetTriple) -> PathStr:
        if triple.libc == "mingw":
             gcc_path = compiler_path.replace("gcc", f"{triple.triple}-gcc")
             if Path(gcc_path).exists():
                return gcc_path

        return compiler_path

    def _get_generator(self, triple: TargetTriple) -> GeneratorStr:
        if triple.target_os == "msys":
            return "MSYS Makefiles"

        if triple.libc == "mingw":
            return "MinGW Makefiles"

        return "NMake Makefiles" if os.name == "nt" else "Unix Makefiles"

    def _scan(self) -> Iterator[CompilerKit]:
        def get_compiler(target):
            cc_name = target["cc_name"]
            cxx_name = target["cxx_name"]

            if compiler_path := self._get_path(cc_name):
                info = self._get_info(compiler_path, target["version_switch"])
                triple = self._get_triple(info)

                cc_path = self._get_cc_path(compiler_path, triple)
                cxx_path = cc_path.replace(cc_name, cxx_name)
                generator = self._get_generator(triple)
                return CompilerKit(cc_name, cc_path, cxx_path, generator)

        for target in self.scan_compilers:
            if compiler := get_compiler(target):
                yield compiler

    def scan(self) -> Iterator[CompilerKit]:
        yield from self._scan()
