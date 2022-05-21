"""cmake script helper"""

import json
import logging
import os
import pathlib
import re
import subprocess
from enum import Enum
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


def build_cache(scope, value):
    """build cache"""

    if not CACHE_DIRECTORY.is_dir():
        CACHE_DIRECTORY.mkdir(parents=True)

    cache = pathlib.Path(CACHE_DIRECTORY, "cmake_script.json")
    cached_data = {}

    # if any data cached
    try:
        with cache.open("r") as file:
            cached_data = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        pass

    cached_data[scope] = value

    with cache.open("w") as file:
        json.dump(cached_data, file, indent=2)


def load_cache(scope):
    """load cache"""

    cache = pathlib.Path(CACHE_DIRECTORY, "cmake_script.json")

    try:
        with cache.open("r") as file:
            cached_data = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        return None
    try:
        return cached_data[scope]
    except KeyError:
        return None


def _get_help(scope, name):
    sout, serr, *_ = exec_subprocess(["cmake", f"--help-{scope}", name])
    return "\n".join([sout, serr])


MODULE_BUILTIN = "builtin"


class NameKind(Enum):
    COMMAND = "command"
    MODULE = "module"
    POLICY = "policy"
    PROPERTY = "property"
    VARIABLE = "variable"


class BaseName(dict):
    """BaseName"""

    @classmethod
    def new(cls, name: str, help: str, kind_: NameKind, module: str):
        return cls({"name": name, "help": help, "kind": kind_.value, "module": module})

    @property
    def name(self):
        return self["name"]

    @property
    def help(self):
        return self["help"]

    @property
    def kind(self):
        return self["kind"]

    @property
    def module(self):
        return self["module"]


def get_commands(cache=True) -> Dict[str, BaseName]:
    scope = "command"
    if cache:
        if cache_data := load_cache(scope):
            return {name: BaseName(data) for name, data in cache_data.items()}

    sout, *_ = exec_subprocess(["cmake", "--help-command-list"])
    data = {
        name: BaseName.new(
            name, _get_help(scope, name), NameKind.COMMAND, MODULE_BUILTIN
        )
        for name in sout.splitlines()
    }
    build_cache(scope, data)
    return data


def get_modules(cache=True) -> Dict[str, BaseName]:
    scope = "module"
    if cache:
        if cache_data := load_cache(scope):
            return {name: BaseName(data) for name, data in cache_data.items()}

    sout, *_ = exec_subprocess(["cmake", "--help-module-list"])
    data = {
        name: BaseName.new(
            name, _get_help(scope, name), NameKind.MODULE, MODULE_BUILTIN
        )
        for name in sout.splitlines()
    }
    build_cache(scope, data)
    return data


def get_policies(cache=True) -> Dict[str, BaseName]:
    scope = "policy"
    if cache:
        if cache_data := load_cache(scope):
            return {name: BaseName(data) for name, data in cache_data.items()}

    sout, *_ = exec_subprocess(["cmake", "--help-policy-list"])
    data = {
        name: BaseName.new(
            name, _get_help(scope, name), NameKind.POLICY, MODULE_BUILTIN
        )
        for name in sout.splitlines()
    }
    build_cache(scope, data)
    return data


def get_properties(cache=True) -> Dict[str, BaseName]:
    scope = "property"
    if cache:
        if cache_data := load_cache(scope):
            return {name: BaseName(data) for name, data in cache_data.items()}

    sout, *_ = exec_subprocess(["cmake", "--help-property-list"])
    data = {
        name: BaseName.new(
            name, _get_help(scope, name), NameKind.PROPERTY, MODULE_BUILTIN
        )
        for name in sout.splitlines()
    }
    build_cache(scope, data)
    return data


def get_variables(cache=True) -> Dict[str, BaseName]:
    scope = "variable"
    if cache:
        if cache_data := load_cache(scope):
            return {name: BaseName(data) for name, data in cache_data.items()}

    sout, *_ = exec_subprocess(["cmake", "--help-variable-list"])
    data = {
        name: BaseName.new(
            name, _get_help(scope, name), NameKind.VARIABLE, MODULE_BUILTIN
        )
        for name in sout.splitlines()
    }
    build_cache(scope, data)
    return data


class Scope(Enum):
    COMMAND = "command"
    SETTER = "setter"
    ACCESS = "access"
    INCLUDE = "include"
    PARAMS = "params"
    VALUE = "value"
    UNKNOWN = "unknown"


class Script:
    """script helper"""

    command_pattern = re.compile(r"^\s*(\w*)$", flags=re.IGNORECASE)
    setter_pattern = re.compile(r"set\((\w*)$", flags=re.IGNORECASE)
    access_pattern = re.compile(r"\${(\w*)$", flags=re.IGNORECASE)
    include_pattern = re.compile(r"include\((\w*)$", flags=re.IGNORECASE)
    params_pattern = re.compile(r"\w+\((\w*)$", flags=re.IGNORECASE)
    value_pattern = re.compile(r"\w+\(\w+ (?:\w+ )*(\w*)$", flags=re.IGNORECASE)

    def __init__(self, source: str):
        self.source = source

    def get_scope(self, line, column):
        lines = self.source.split("\n")

        current_line = lines[line]
        current_line_text = current_line[:column]

        LOGGER.debug(f"get scope for {current_line_text}")

        if found := self.command_pattern.search(current_line_text):
            return (Scope.COMMAND, found.group(1))

        if found := self.setter_pattern.search(current_line_text):
            return (Scope.SETTER, found.group(1))

        if found := self.access_pattern.search(current_line_text):
            return (Scope.ACCESS, found.group(1))

        if found := self.include_pattern.search(current_line_text):
            return (Scope.INCLUDE, found.group(1))

        if found := self.params_pattern.search(current_line_text):
            return (Scope.PARAMS, found.group(1))

        if found := self.value_pattern.search(current_line_text):
            return (Scope.VALUE, found.group(1))

        return (Scope.UNKNOWN, "")

    def get_candidates(self, scope):
        LOGGER.debug(f"get candidates for {scope}")

        if scope == Scope.COMMAND:
            return get_commands()

        if any([scope == Scope.SETTER, scope == Scope.ACCESS, scope == Scope.VALUE]):
            return {**get_variables(), **get_properties()}

        if scope == Scope.INCLUDE:
            return get_modules()

        if scope == Scope.PARAMS:
            return {**get_modules(), **get_variables(), **get_properties()}

        # unknown
        return {}

    def complete(self, line, column) -> Optional[BaseName]:
        scope, _ = self.get_scope(line, column)
        return [value for (name, value) in self.get_candidates(scope).items()]

    def help(self, line, column) -> Optional[BaseName]:
        scope, identifier = self.get_scope(line, column)
        return self.get_candidates(scope).get(identifier, None)


def complete(src, line, column) -> Optional[BaseName]:
    return Script(src).complete(line, column)


def documentation(src, line, column) -> Optional[BaseName]:
    return Script(src).help(line, column)
