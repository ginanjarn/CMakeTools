"""cmake commands"""

import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Iterable, Iterator, Any


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

    # ensure if cwd is directory
    if not (cwd and Path(cwd).is_dir()):
        cwd = None

    # update from current environment
    if env:
        environ = os.environ
        env = environ.update(env)
        env = environ

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

    # wait() method return 'returncode' after process terminated.
    return process.wait()


class DefaultWriter(StreamWriter):
    def write(self, s: str) -> int:
        n = sys.stderr.write(s)
        return n


def normalize(commands: Iterable[Any]) -> Iterator[str]:
    """normalize commands to str"""
    for command in commands:
        if isinstance(command, Path):
            yield command.as_posix()
        else:
            yield str(command)


class CMakeConfigureCommand:
    def __init__(self, executable: Path, source: Path, build: Path):
        self._commands = [executable, "-S", source, "-B", build]
        self._commands.extend(
            ["--no-warn-unused-cli", "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE"]
        )

    def command(self) -> List[str]:
        return list(normalize(self._commands))

    def set_generator(self, generator: str):
        if generator:
            self._commands.extend(["-G", generator])
        return self

    def set_cmake_variables(self, variables: Dict[str, Any]):
        if variables:
            variables = [f"-D{k}={v}" for k, v in variables.items()]
            self._commands.extend(variables)
        return self


class CMakeBuildCommand:
    def __init__(self, executable: Path, build: Path):
        self._commands = [executable, "--build", build]

    def command(self) -> List[str]:
        return list(normalize(self._commands))

    def set_config(self, config: str):
        if config:
            self._commands.extend(["--config", config])
        return self

    def set_target(self, target: str):
        if target:
            self._commands.extend(["--target", target])
        return self

    def set_parallel_jobs(self, njobs):
        if njobs:
            self._commands.extend(["-j", njobs])
        return self


class CTestCommand:
    def __init__(self, executable: Path, build: Path):
        self._commands = [executable, "--test-dir", build, "--output-on-failure"]

    def command(self) -> List[str]:
        return list(normalize(self._commands))

    def set_config(self, config: str):
        if config:
            self._commands.extend(["--config", config])
        return self

    def set_target(self, target: str):
        if target:
            self._commands.extend(["--target", target])
        return self

    def set_parallel_jobs(self, njobs):
        if njobs:
            self._commands.extend(["-j", njobs])
        return self
