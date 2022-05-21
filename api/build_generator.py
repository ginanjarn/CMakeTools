"""build generator"""

import json
import logging
import os
import pathlib
import re
import subprocess
from dataclasses import dataclass
from io import StringIO
from typing import Iterable, Tuple, List, Optional, Dict, Any

LOGGER = logging.getLogger(__name__)
# LOGGER.setLevel(logging.DEBUG)  # module logging level
STREAM_HANDLER = logging.StreamHandler()
LOG_TEMPLATE = "%(levelname)s %(asctime)s %(filename)s:%(lineno)s  %(message)s"
STREAM_HANDLER.setFormatter(logging.Formatter(LOG_TEMPLATE))
LOGGER.addHandler(STREAM_HANDLER)


def exec_subprocess(
    command: Iterable[str], *, input: str = None, cwd: str = None
) -> Tuple[str, str, int]:
    """exec subprocess

    Return:
        Tuple[stdout: str, stderr: str, returncode: int]

    Raises:
        OSError
    """
    LOGGER.debug(f"command: {command}")
    startupinfo = None
    if os.name == "nt":
        # if on Windows, hide process window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ,
            bufsize=0,  # no buffering
            startupinfo=startupinfo,
        )
    except FileNotFoundError as err:
        raise FileNotFoundError(f"'{command[0]}' not found in PATH") from err

    if input is not None:
        input = input.encode()

    def normalize_newline(src: bytes):
        return src.replace(b"\r\n", b"\n")

    sout, serr = process.communicate(input)
    sout = normalize_newline(sout)
    serr = normalize_newline(serr)
    return sout.decode(), serr.decode(), process.returncode


CACHE_DIRECTORY_NAME = "CMakeTools"
CACHE_DIRECTORY = (
    pathlib.Path().home().joinpath("AppData", "Local", CACHE_DIRECTORY_NAME)
)
if os.name != "nt":
    CACHE_DIRECTORY = pathlib.Path().home().joinpath(CACHE_DIRECTORY_NAME)

generator_pattern = re.compile(r"^[\* ] ((?:[A-Z][\w ]+|\- |\d+ )+)")


def scan_generators() -> Iterable[str]:
    sout, *_ = exec_subprocess(["cmake", "-h"])
    for line in sout.splitlines():
        match = generator_pattern.match(line)
        if match:
            yield match.group(1).strip()


def _build_generators_cache() -> None:
    if not CACHE_DIRECTORY.is_dir():
        CACHE_DIRECTORY.mkdir(parents=True)

    cache = pathlib.Path(CACHE_DIRECTORY, "generators.txt")
    with cache.open("w") as file:
        data = "\n".join(scan_generators())
        file.write(data)


def _load_generators_cache() -> List[str]:
    cache = pathlib.Path(CACHE_DIRECTORY, "generators.txt")
    with cache.open("r") as file:
        return file.read().splitlines()


def get_generators() -> List[str]:
    """get cmake generators"""
    cache = pathlib.Path(CACHE_DIRECTORY, "generators.txt")
    if not cache.is_file():
        _build_generators_cache()

    return _load_generators_cache()


@dataclass(order=True)
class CompilerDefinition:
    c_executable: str = ""
    cxx_executable: str = ""
    versionFlag: str = ""
    targetRegex: str = ""
    versionRegex: str = ""


@dataclass(order=True)
class CompilerData:
    name: str = ""
    target: str = ""
    version: str = ""
    c_path: str = ""
    cxx_path: str = ""

    def to_dict(self):
        return {
            "name": self.name,
            "target": self.target,
            "version": self.version,
            "c_path": self.c_path,
            "cxx_path": self.cxx_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            name=data.get("name", ""),
            target=data.get("target", ""),
            version=data.get("version", ""),
            c_path=data.get("c_path", ""),
            cxx_path=data.get("cxx_path", ""),
        )


COMPILERS = [
    CompilerDefinition(
        "clang", "clang++", "-v", r"Target:\s*([\w\-]+)", r"version\s*(\d+\.\d+\.\d+)"
    ),
    CompilerDefinition(
        "gcc", "g++", "-v", r"Target:\s*([\w\-]+)", r"gcc\s*(\d+\.\d+\.\d+)"
    ),
]


def scan_compilers() -> Iterable[CompilerData]:
    def scan(compiler):
        # get compiler definition
        compiler_data = CompilerData()
        _, serr, *_ = exec_subprocess([compiler.c_executable, compiler.versionFlag])

        # get target
        found = re.search(compiler.targetRegex, serr, flags=re.MULTILINE)
        if found:
            target = found.group(1)
            compiler_data.target = target

        # get version
        found = re.search(compiler.versionRegex, serr, flags=re.MULTILINE)
        if found:
            version = found.group(1)
            compiler_data.version = version

        compiler_data.name = f"{compiler.c_executable.upper()} {target} {version}"

        c_compiler = compiler.c_executable
        cxx_compiler = compiler.cxx_executable

        # mingw rename c compiler starts with target
        compiler_target = compiler_data.target

        if "mingw" in compiler_target:
            c_compiler = f"{compiler_target}-{compiler.c_executable}"
            cxx_compiler = f"{compiler_target}-{compiler.cxx_executable}"

        # get compiler path
        locate_command = "where" if os.name == "nt" else "which"

        sout, *_ = exec_subprocess([locate_command, c_compiler])
        compiler_data.c_path = sout.strip()

        sout, *_ = exec_subprocess([locate_command, cxx_compiler])
        compiler_data.cxx_path = sout.strip()

        LOGGER.debug(f"compiler: {compiler_data}")
        return compiler_data

    for compiler in COMPILERS:
        try:
            result = scan(compiler)
        except FileNotFoundError:
            LOGGER.info(f"{compiler.c_executable} not found")
        except Exception as err:
            LOGGER.error(f"scan error --> {err}", exc_info=True)
        else:
            yield result


def _build_compiler_cache() -> None:
    """build compiler cache"""

    if not CACHE_DIRECTORY.is_dir():
        CACHE_DIRECTORY.mkdir(parents=True)

    cache = pathlib.Path(CACHE_DIRECTORY, "compilers.json")
    compilers = scan_compilers()

    with cache.open("w") as file:
        data = [compiler.to_dict() for compiler in compilers]
        json.dump(data, file, indent=2)


def _load_compiler_cache() -> List[CompilerData]:
    """load compiler from cache"""

    cache = pathlib.Path(CACHE_DIRECTORY, "compilers.json")
    with cache.open("r") as file:
        datas = json.load(file)
        return [CompilerData.from_dict(data) for data in datas]


def get_compilers(scan: bool = False) -> List[CompilerData]:
    """get compiler data"""
    cache = pathlib.Path(CACHE_DIRECTORY, "compilers.json")

    if scan or not cache.is_file():
        _build_compiler_cache()

    return _load_compiler_cache()


# project type
TYPE_EXECUTABLE = "executable"
TYPE_LIBRARY = "library"
# build mode
MODE_DEBUG = "Debug"
MODE_RELEASE = "Release"


CPP_LIBRARY_H_SNIPPET = """\
void sayHello();
"""
CPP_LIBRARY_SNIPPET = """\
#include <iostream>

void sayHello(){
    std::cout << "hello";
}
"""

CPP_EXECUTABLE_SNIPPET = """\
#include <iostream>

int main(int argc, char const *argv[]){
    std::cout << "hello";
}
"""


def cmakelists_snippet(name: str, project_type: int, version: Optional[str] = None, /):
    """get cmakelists snipper"""

    version = version if version else "0.1.0"
    snippet = StringIO()

    snippet.write(
        "cmake_minimum_required(VERSION 3.0.0)\n"
        f"project({name} VERSION {version})\n\n"
        "include(CTest)\nenable_testing()\n\n"
    )

    if project_type == TYPE_EXECUTABLE:
        snippet.write(f"add_executable({name} main.cpp)\n\n")
    elif project_type == TYPE_LIBRARY:
        snippet.write(f"add_library({name} {name}.cpp {name}.h)\n\n")
    else:
        raise ValueError(f"invalid project_type '{project_type}'")

    snippet.write(
        "set(CPACK_PROJECT_NAME ${PROJECT_NAME})\n"
        "set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})\n"
        "include(CPack)\n"
    )
    return snippet.getvalue()


def create_project_snippet(
    path: str, name: str, project_type: int, version: Optional[str] = None
):
    os.chdir(os.path.abspath(path))
    version = version if version else "0.1.0"

    with open("CMakelists.txt", "w") as file:
        file.write(cmakelists_snippet(name, project_type, version))

    if project_type == TYPE_EXECUTABLE:
        with open("main.cpp", "w") as file:
            file.write(CPP_EXECUTABLE_SNIPPET)

    elif project_type == TYPE_LIBRARY:
        with open(f"{name}.h", "w") as file:
            file.write(CPP_LIBRARY_H_SNIPPET)
        with open(f"{name}.cpp", "w") as file:
            file.write(CPP_LIBRARY_SNIPPET)


def generate_project(path, *, generator=None, c_path=None, cxx_path=None):
    """create new project"""

    src_path = pathlib.Path(path)
    build_path = pathlib.Path(path, "build")

    command = [
        "cmake",
        "--no-warn-unused-cli",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE",
        "-DCMAKE_BUILD_TYPE:STRING=Debug",
        f"-S{src_path}",
        f"-B{build_path}",
    ]

    if c_path:
        command.append(f"-DCMAKE_C_COMPILER:FILEPATH={c_path}")
    if cxx_path:
        command.append(f"-DCMAKE_CXX_COMPILER:FILEPATH={cxx_path}")

    if generator:
        command.extend(["-G", generator])

    sout, serr, *_ = exec_subprocess(command, cwd=path)
    return "\n".join([sout, serr])


def build(path, build_mode=MODE_DEBUG, n_jobs=None):
    """build project"""

    # expand path
    path = os.path.abspath(path)

    build_path = pathlib.Path(path, "build")

    command = [
        "cmake",
        "--build",
        build_path,
        "--config",
        build_mode,
        "--target",
        "all",
    ]

    if n_jobs is not None:
        command.extend(
            ["-j", n_jobs, "--",]
        )

    sout, serr, *_ = exec_subprocess(command, cwd=path)
    return "\n".join([sout, serr])
