""""""

import html
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Iterator


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


def get_childprocess(command: List[str]) -> str:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=STARTUPINFO,
    )
    sout, serr = process.communicate()
    if ret := process.returncode:
        print(serr.strip().decode(), file=sys.stderr)
        raise OSError(f"process terminated with exit code {ret}")
    return sout.strip().decode()


HelpType = str


@dataclass
class CMakeHelpItem:
    type: HelpType
    name: str

    def get_docstring(self) -> str:
        """return .rst formatted docstring"""
        command = ["cmake", f"--help-{self.type}", self.name]
        doc = get_childprocess(command)
        return doc


def _get_helps(type: HelpType = "") -> Iterator[CMakeHelpItem]:
    command = ["cmake", f"--help-{type}-list"]
    result = get_childprocess(command)
    yield from (CMakeHelpItem(type, item) for item in result.splitlines())


HELP_TYPES = ["command", "variable", "property", "module"]


def get_helps(type: HelpType = "") -> Iterator[CMakeHelpItem]:
    """get available helps"""

    if type in HELP_TYPES:
        yield from _get_helps(type)
        return

    for type in HELP_TYPES:
        yield from _get_helps(type)


def get_docstring(help: CMakeHelpItem) -> str:
    """get docstring markdown compatible"""

    # due to incompatibility between '.rst' with markdown, wrap docstring with pre
    return "<pre>" + html.escape(help.get_docstring()) + "</pre>"
