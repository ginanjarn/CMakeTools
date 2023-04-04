""""""

import html
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from enum import Enum
from typing import List, Iterator


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


def exec_cmd(command: List[str]) -> str:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=STARTUPINFO,
    )
    sout, serr = process.communicate()
    if (ret := process.poll()) and ret != 0:
        print(serr.strip().decode(), file=sys.stderr)
        raise OSError(f"process terminated with exit code {ret}")
    return sout.strip().decode()


NameStr = str
DocumentStr = str
TypeStr = str


class NameType(Enum):
    Command = "command"
    Module = "module"
    Property = "property"
    Variable = "variable"


@lru_cache(maxsize=512)
def get_cmake_names(type: NameType) -> List[NameStr]:
    try:
        command = ["cmake", f"--help-{type.value}-list"]
    except AttributeError as err:
        raise TypeError(f"type must {NameType!r}") from err

    return exec_cmd(command).splitlines()


@lru_cache(maxsize=512)
def get_cmake_documentation(type: NameType, name: NameStr) -> DocumentStr:
    try:
        command = ["cmake", f"--help-{type.value}", name]
    except AttributeError as err:
        raise TypeError(f"type must {NameType!r}") from err

    return exec_cmd(command)


@dataclass
class Name:
    name: NameStr
    type: NameType
    docstring: DocumentStr = ""


class Proxy:
    """Proxy helper for fetching cmake help commands"""

    def _get_all_names(self) -> Iterator[Name]:

        commands = get_cmake_names(NameType.Command)
        for command in commands:
            yield Name(command, NameType.Command)

        modules = get_cmake_names(NameType.Module)
        for module in modules:
            yield Name(module, NameType.Module)

        properties = get_cmake_names(NameType.Property)
        for property in properties:
            yield Name(property, NameType.Property)

        variables = get_cmake_names(NameType.Variable)
        for variable in variables:
            yield Name(variable, NameType.Variable)

    def get_all_names(self) -> List[Name]:
        return list(self._get_all_names())

    def get_documentation(self, name: NameStr) -> DocumentStr:
        cnames = self.get_all_names()
        found_index = -1
        for index, cname in enumerate(cnames):
            if cname.name == name:
                found_index = index
                break
        if found_index < 0:
            raise ValueError(f"name not found: {name!r}")

        doc = get_cmake_documentation(cnames[found_index].type, name)
        return doc


class Script:
    def __init__(self, source: str):
        self.source = source
        self._proxy = Proxy()

    def _get_word_at(self, row: int, col: int) -> str:
        lines = self.source.split("\n")
        occur_line = lines[row]

        if (lines_len := len(lines)) and row >= lines_len:
            raise ValueError(f"params row ({row}) not in valid range (0-{lines_len})")

        if (line_len := len(occur_line)) and col > line_len:
            raise ValueError(f"params column ({col}) not in valid range (0-{line_len})")

        for found in re.finditer(r"(\w+)", occur_line):
            if found.start() <= col <= found.end():
                return found.group(1)

        raise ValueError(f"no identifier found at row: {row}, column:{col}")

    def help(self, row: int, col: int) -> Name:
        try:
            name = self._get_word_at(row, col)
            doc = self._proxy.get_documentation(name)

        except ValueError:
            return ""
        else:
            return f"<pre>{html.escape(doc)}</pre>"

    def complete(self, row: int, col: int) -> Name:
        return self._proxy.get_all_names()
