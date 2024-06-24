"""cmake commands"""

import os
import shlex
import sys
import subprocess
from multiprocessing import cpu_count
from pathlib import Path
from typing import List, Dict, Any


BUILD_TYPES = [
    "Debug",
    "Release",
    "RelWithDebInfo",
    "MinSizeRel",
]

if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


class StreamWriter:
    """Stream writer interface"""

    def write(self, s: str) -> int:
        raise NotImplementedError


class Command:
    """Base subprocess command"""

    def get_command(self) -> List[str]:
        """get command"""


ReturnCode = int


def normalize_command(command: List[Any]) -> List[str]:
    """normalize command to str"""
    return [str(c) for c in command]


def exec_subprocess(
    command: Command, output: StreamWriter, /, cwd: Path = None, env: dict = None
) -> ReturnCode:
    commands = normalize_command(command.get_command())

    output.write(f"exec: {shlex.join(commands)}\n")
    proc = subprocess.Popen(
        normalize_command(commands),
        # stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # redirect to stdout
        startupinfo=STARTUPINFO,
        bufsize=0,  # flush buffer
        cwd=cwd,
        shell=True,
        env=env,
    )
    while line := proc.stdout.readline():
        output.write(line.rstrip().decode() + "\n")

    return proc.wait()


class DefaultWriter(StreamWriter):
    """default write to stderr"""

    def write(self, s: str) -> int:
        n = sys.stderr.write(s)
        return n


class CMakeCommands(Command):
    def __init__(self, command: List[str]):
        self._command = command

    def get_command(self):
        return self._command

    @staticmethod
    def cache_entry_to_arguments(cache_entry: Dict[str, str]) -> List[str]:
        """transform cache entry to argument"""

        def quote_value(value: Any) -> str:
            """wrap with quote if value contain space"""
            svalue = str(value)
            if " " in svalue:
                return f'"{value}"'
            return svalue

        return [f"-D{var}={quote_value(val)}" for (var, val) in cache_entry.items()]

    @classmethod
    def configure(
        cls,
        source: Path,
        build: Path,
        *,
        cache_entry: Dict[str, str] = None,
        generator: str = "",
    ):
        command = ["cmake", "-S", str(source.as_posix()), "-B", str(build.as_posix())]

        if cache_entry:
            command.extend(cls.cache_entry_to_arguments(cache_entry))

        if generator:
            command.extend(["-G", generator])

        return cls(command)

    @classmethod
    def build(
        cls,
        build: Path,
        *,
        target: str = "all",
        cache_entry: Dict[str, str] = None,
        njobs: int = -1,
    ):
        command = ["cmake", "--build", str(build)]
        if cache_entry:
            command.extend(cls.cache_entry_to_arguments(cache_entry))

        command.extend(["--target", target])

        njobs = njobs if njobs > 0 else cpu_count()
        command.extend(["-j", njobs])
        return cls(command)

    @classmethod
    def install(cls, build: Path, *, cache_entry: Dict[str, str] = None):
        command = ["cmake", "--install", str(build)]
        if cache_entry:
            command.extend(cls.cache_entry_to_arguments(cache_entry))
        return cls(command)


class CTestCommand(Command):
    def __init__(self, build: Path, *, njobs: int = -1):
        self._command = ["ctest", "--test-dir", str(build)]

        njobs = njobs if njobs > 0 else cpu_count()
        self._command.extend(["-j", njobs])

    def get_command(self):
        return self._command
