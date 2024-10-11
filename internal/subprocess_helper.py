import os
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Any

ReturnCode = int


class StreamWriter(ABC):
    @abstractmethod
    def write(self, value: str):
        """write to stream"""


def normalize_command(command: List[Any]) -> List[str]:
    """normalize command to str"""
    return [str(c) for c in command]


class CaptureOption(Enum):
    NONE = 0
    STDERR = 2
    STDOUT = 4
    ALL = 8


def exec_subprocess(
    command: List[str],
    output: StreamWriter,
    /,
    captures: CaptureOption = CaptureOption.ALL,
    cwd: Path = None,
    env: dict = None,
) -> ReturnCode:
    commands = normalize_command(command)

    stdout = stderr = subprocess.DEVNULL
    if captures == CaptureOption.STDOUT:
        stdout = subprocess.PIPE

    if captures == CaptureOption.STDERR:
        # redirect stderr to stdout
        stderr = subprocess.STDOUT

    if captures == CaptureOption.ALL:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT

    proc = subprocess.Popen(
        normalize_command(commands),
        # stdin=subprocess.PIPE,
        stdout=stdout,
        stderr=stderr,
        startupinfo=STARTUPINFO,
        bufsize=0,  # flush buffer
        cwd=cwd,
        shell=True,
        env=env,
    )
    while line := proc.stdout.readline():
        output.write(line.rstrip().decode() + "\n")

    return proc.wait()


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None
