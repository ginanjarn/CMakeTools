"""cmake commands"""

import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import List, Optional, Iterable, Iterator, Any


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


def normalize(commands: Iterable[Any]) -> Iterator[str]:
    for command in commands:
        if isinstance(command, Path):
            yield command.as_posix()
        else:
            yield str(command)


class CMakeCommand:
    def __init__(self, executable: Path, *args):
        self._commands = [executable, *args]

    def command(self):
        return list(normalize(self._commands))

    @classmethod
    def configure(
        cls,
        executable: Path,
        source: Path,
        build: Path,
        *,
        generator: str = "",
        cache_entry: dict = None,
        options: List[str] = None,
    ):
        entries = [f"-D{k}={v}" for k, v in cache_entry.items()] if cache_entry else []
        generator_arg = ["-G", generator] if generator else []
        options = options or []
        options.extend(
            ["--no-warn-unused-cli", "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE"]
        )

        return cls(
            executable, "-S", source, "-B", build, *entries, *generator_arg, *options
        )

    @classmethod
    def build(
        cls,
        executable: Path,
        build: Path,
        *,
        config: str = "Debug",
        target: str = "all",
        njobs: int = 4,
        options: List[str] = None,
    ):
        args = ["--config", config, "--target", target, "-j", njobs]
        options = options or []
        return cls(executable, "--build", build, *args, *options, "--")

    @classmethod
    def install(
        cls,
        executable: Path,
        build: Path,
        *,
        config: str = "Debug",
        options: List[str] = None,
    ):
        args = ["--config", config]
        options = options or []
        return cls(executable, "--install", build, *args, *options)


class CTestCommand:
    def __init__(self, executable: Path, *args):
        self._commands = [executable, *args]

    def command(self):
        return list(normalize(self._commands))

    @classmethod
    def ctest(
        cls,
        executable: Path,
        build: Path,
        *,
        config: str = "Debug",
        target: str = "test",
        njobs: int = 4,
        options: List[str] = None,
    ):
        options = options or []
        options.extend(["-j", njobs, "-C", config, "-T", target, "--output-on-failure"])
        return cls(executable, "--test-dir", build, *options)
