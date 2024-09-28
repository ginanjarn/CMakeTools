from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Iterator

from .subprocess_helper import exec_subprocess, CaptureOption

PathStr = str


class NameType(Enum):
    """"""

    Command = "command"
    Module = "module"
    Policy = "policy"
    Property = "property"
    Variable = "variable"


class Name:
    """"""

    __slots__ = ["name", "type"]

    def __init__(self, name: str, type: NameType):
        self.name = name
        self.type = NameType(type)

    def __repr__(self):
        return f"Name(name={self.name!r},type={self.type.value!r})"


class HelpCLI:
    """"""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def get_name_list(self, file: PathStr = "") -> Iterator[Name]:
        """"""
        for type in NameType:
            yield from self.get_name_for_type(type, file)

    def get_name_for_type(self, type: NameType, file: PathStr = "") -> Iterator[Name]:
        """"""
        command = ["cmake", f"--help-{type.value}-list"]
        if file:
            command.append(file)

        buffer = StringIO()
        return_code = exec_subprocess(command, buffer, cwd=self.project_path)
        if return_code != 0:
            return

        for item in buffer.getvalue().splitlines():
            yield Name(item, type)

    def get_documentation(self, name: Name, file: PathStr = "") -> str:
        """"""
        command = ["cmake", f"--help-{name.type.value}", name.name]
        if file:
            command.append(file)

        buffer = StringIO()
        return_code = exec_subprocess(
            command, buffer, captures=CaptureOption.STDOUT, cwd=self.project_path
        )
        if return_code != 0:
            return ""

        return buffer.getvalue()
