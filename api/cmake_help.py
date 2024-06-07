"""CMake Help generator"""

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Dict


if os.name == "nt":
    # if on Windows, hide process window
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None


def exec_subprocess(command: List[str]) -> str:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=STARTUPINFO,
    )
    sout, serr = process.communicate()
    if process.returncode != 0:
        print(serr.strip().decode(), file=sys.stderr)
        raise OSError(f"process terminated with exit code {process.returncode}")
    return sout.strip().decode()


@dataclass
class HelpItem:
    name: str
    kind: str


class HelpCache:
    def __init__(self):
        self.help_items: Dict[str, HelpItem] = {}

    def load_help_items(self):
        self.help_items.update({item.name: item for item in self.command_list()})
        self.help_items.update({item.name: item for item in self.command_list()})
        self.help_items.update({item.name: item for item in self.variable_list()})
        self.help_items.update({item.name: item for item in self.module_list()})

    def get_help_item(self, name: str) -> HelpItem:
        if not self.help_items:
            self.load_help_items()

        return self.help_items.get(name)

    def get_help_item_list(self, *, kind: str = "") -> List[HelpItem]:
        if not self.help_items:
            self.load_help_items()

        if kind:
            return [item for _, item in self.help_items.items() if item.kind == kind]

        return [item for _, item in self.help_items.items()]

    def get_cmake_help_list(self, kind: str) -> List[HelpItem]:
        command = ["cmake", f"--help-{kind}-list"]
        name_lines = exec_subprocess(command)
        items = [HelpItem(name, kind) for name in name_lines.splitlines()]
        return items

    def get_cmake_documentation(self, name: str, kind: str) -> str:
        command = ["cmake", f"--help-{kind}", name]
        documentation = exec_subprocess(command)
        return documentation.replace("\r\n", "\n")

    def command_list(self) -> List[HelpItem]:
        item_kind = "command"
        return self.get_cmake_help_list(item_kind)

    def variable_list(self) -> List[HelpItem]:
        item_kind = "variable"
        return self.get_cmake_help_list(item_kind)

    def property_list(self) -> List[HelpItem]:
        item_kind = "property"
        return self.get_cmake_help_list(item_kind)

    def module_list(self) -> List[HelpItem]:
        item_kind = "module"
        return self.get_cmake_help_list(item_kind)
