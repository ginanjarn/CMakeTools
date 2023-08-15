"""cmake commands"""

import os
import sys
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Params:
    """Base Params object"""

    def command(self) -> List[str]:
        raise NotImplementedError


BUILD_TYPES = [
    "Debug",
    "Release",
    "RelWithDebInfo",
    "MinSizeRel",
]


class StreamWriter:
    """Stream writer interface"""

    def write(self, s: str) -> int:
        raise NotImplementedError


def exec_childprocess(
    command: List[str],
    writer: StreamWriter,
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> int:
    """exec_childprocess, write result to writer object"""

    if isinstance(command, str):
        command = shlex.split(command)

    print(f"execute '{shlex.join(command)}'")

    process = subprocess.Popen(
        command,
        # stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # redirect to stdout
        startupinfo=STARTUPINFO,
        bufsize=0,
        cwd=cwd,
        shell=True,
        env=env,
    )

    while line := process.stdout.readline():
        writer.write(line.rstrip().decode() + "\n")

    return process.poll()


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


class DefaultWriter(StreamWriter):
    def write(self, s: str) -> int:
        n = sys.stderr.write(s)
        return n


GeneratorKit = str
Target = str
BuildType = str


@dataclass
class Configure(Params):
    build_type: BuildType
    c_compiler: Path
    cxx_compiler: Path
    source_path: Path
    build_path: Path
    generator: GeneratorKit

    def command(self) -> List[str]:
        cmd = [
            "cmake",
            "--no-warn-unused-cli",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE",
            f"-S{Path(self.source_path).as_posix()}",
            f"-B{Path(self.build_path).as_posix()}",
        ]

        if self.build_type:
            cmd.append(f"-DCMAKE_BUILD_TYPE:STRING={self.build_type}")
        if self.c_compiler:
            cmd.append(f"-DCMAKE_C_COMPILER:FILEPATH={self.c_compiler}")
        if self.c_compiler:
            cmd.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={self.cxx_compiler}")

        if self.generator:
            cmd.extend(
                [
                    "-G",
                    self.generator,
                ]
            )

        return cmd


@dataclass
class Build(Params):
    build_path: Path
    config: BuildType
    target: Target
    njobs: int = 4

    def command(self) -> List[str]:
        return [
            "cmake",
            "--build",
            self.build_path.as_posix(),
            "--config",
            self.config,
            "--target",
            "all",
            "-j4",
            "--",
        ]


@dataclass
class CTest(Params):
    build_path: Path
    config: BuildType

    def command(self) -> List[str]:
        return [
            "ctest",
            "-j4",
            "-C",
            self.config,
            "-T",
            "test",
            "--output-on-failure",
        ]
