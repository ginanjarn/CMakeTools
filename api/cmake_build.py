"""cmake build helper"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any

if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


@dataclass
class ExecResult:
    returncode: int
    stdout: str
    stderr: str


def exec_cmd_nobuffer(command: List[str], **kwargs: Any) -> int:
    """exec command and write result to stderr

    return exit code
    """

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

    def listen_stderr():
        while True:
            if line := process.stderr.readline():
                print(line.strip().decode())
            else:
                return

    def listen_stdout():
        while True:
            if line := process.stdout.readline():
                print(line.strip().decode())
            else:
                return

    sout_thread = threading.Thread(target=listen_stdout, daemon=True)
    serr_thread = threading.Thread(target=listen_stderr, daemon=True)
    sout_thread.start()
    serr_thread.start()

    # wait until process done
    while process.poll() is None:
        time.sleep(0.5)

    return process.poll()


PathStr = str
BuildTypeStr = str
ReturnCode = int

BUILD_TYPES = [
    "Debug",
    "Release",
    "RelWithDebInfo",
    "MinSizeRel",
]


def configure(
    source_dir: PathStr, cc_path: PathStr, cxx_path: PathStr, generator: str
) -> ReturnCode:
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

    ret = exec_cmd_nobuffer(command)
    print(f"execution terminated with exit code {ret}")
    return ret


def build(
    build_dir: PathStr,
    build_type: BuildTypeStr = "",
) -> ReturnCode:
    """build project

    execute 'cmake build'
    """

    build_type = build_type or "Debug"
    command = [
        "cmake",
        "--build",
        build_dir,
        "--config",
        build_type,
        "--target",
        "all",
        "-j",
        "4",
        "--",
    ]

    ret = exec_cmd_nobuffer(command)
    print(f"execution terminated with exit code {ret}")
    return ret


def ctest(
    source_dir: PathStr,
    build_type: BuildTypeStr = "",
) -> ReturnCode:
    """run test project

    execute 'ctest'
    """

    build_type = build_type or "Debug"
    command = ["ctest", "-j4", "-C", build_type, "-T", "test", "--output-on-failure"]

    ret = exec_cmd_nobuffer(command, cwd=source_dir)
    print(f"execution terminated with exit code {ret}")
    return ret
