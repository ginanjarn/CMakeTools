"""cmake build helper"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any

PathStr = str
BuildTypeStr = str
ReturnCode = int

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


@dataclass
class ExecResult:
    returncode: ReturnCode
    stdout: str
    stderr: str

    def text(self) -> str:
        """text of concatenated stdout and stderr"""
        temp = []
        if self.stdout:
            temp.append(self.stdout)
        if self.stderr:
            temp.append(self.stderr)
        return "\n".join(temp)


def exec_cmd(command: List[str], **kwargs: Any) -> ExecResult:
    """exec command"""

    print(f"execute {command}")

    process = subprocess.Popen(
        command,
        # stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=STARTUPINFO,
        bufsize=0,
        cwd=kwargs.get("cwd"),
    )

    sout, serr = process.communicate()
    return ExecResult(
        process.returncode,
        sout.replace(b"\r", b"").decode(),
        serr.replace(b"\r", b"").decode(),
    )


def configure(
    source_dir: PathStr, cc_path: PathStr, cxx_path: PathStr, generator: str
) -> ExecResult:
    """configure project"""

    source_dir = Path(source_dir)
    build_dir = source_dir.joinpath("build")

    command = [
        "cmake",
        "--no-warn-unused-cli",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE",
        "-DCMAKE_BUILD_TYPE:STRING=Debug",
        f"-DCMAKE_C_COMPILER:FILEPATH={cc_path}",
        f"-DCMAKE_CXX_COMPILER:FILEPATH={cxx_path}",
        f"-S{source_dir.as_posix()}",
        f"-B{build_dir.as_posix()}",
        "-G",
        generator,
    ]

    return exec_cmd(command)


def build(
    build_dir: PathStr,
    build_type: BuildTypeStr = "",
) -> ExecResult:
    """build project"""

    build_type = build_type or "Debug"
    command = [
        "cmake",
        "--build",
        build_dir,
        "--config",
        build_type,
        "--target",
        "all",
        "-j4",
        "--",
    ]

    return exec_cmd(command)


def ctest(
    build_dir: PathStr,
    build_type: BuildTypeStr = "",
) -> ExecResult:
    """test project"""

    build_type = build_type or "Debug"
    command = ["ctest", "-j4", "-C", build_type, "-T", "test", "--output-on-failure"]

    return exec_cmd(command, cwd=build_dir)
