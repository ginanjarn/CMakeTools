import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional

from .subprocess_helper import exec_subprocess, StreamWriter, ReturnCode


def posix_path(path: str) -> str:
    return Path(path).as_posix()


@dataclass
class Command:
    """Command base"""

    def command(self) -> List[str]:
        """"""
        raise NotImplementedError("'command()' not implemented")


@dataclass
class Configure(Command):
    source: str = ""
    build: str = ""
    generator: str = ""
    cache_entry: Dict[str, Any] = field(default_factory=dict)
    toolchain: str = ""
    install_prefix: str = ""

    def command(self) -> List[str]:
        c = ["cmake"]
        if self.source:
            c.extend(["-S", f"{posix_path(self.source)}"])
        if self.build:
            c.extend(["-B", f"{posix_path(self.build)}"])
        if self.generator:
            c.extend(["-G", f"{self.generator}"])
        if self.cache_entry:
            c.extend(
                [
                    f"-D{k}={shlex.quote(str(v))}"
                    for k, v in self.cache_entry.items()
                    if v
                ]
            )
        if self.toolchain:
            c.extend(["--toolchain", f"{self.toolchain}"])
        if self.install_prefix:
            c.extend(["--install-prefix", f"{self.install_prefix}"])
        return c


@dataclass
class Build(Command):
    build: str = ""
    target: str = ""

    def command(self) -> List[str]:
        c = ["cmake"]
        if self.build:
            c.extend(["--build", posix_path(self.build)])
        else:
            c.extend(["--build", "."])
        if self.target:
            c.extend(["--target", self.target])
        return c


@dataclass
class Test(Command):
    build: str = ""
    test_regex: str = ""

    def command(self) -> List[str]:
        c = ["ctest", "--output-on-failure"]
        if self.build:
            c.extend(["--test-dir", posix_path(self.build)])
        if self.test_regex:
            c.extend(["-R", self.test_regex])
        return c


@dataclass
class Script(Command):
    file: str

    def command(self) -> List[str]:
        return ["cmake", "-P", self.file]


class PresetsCommand(Command):
    cmd: List[str]
    name: str

    def command(self) -> List[str]:
        if not isinstance(self.cmd, list):
            raise ValueError("'cmd' must a list command")
        self.cmd.extend(["--presets", self.name])

    @classmethod
    def configure(cls, presets: str):
        return cls(["cmake"], presets)

    @classmethod
    def build(cls, presets: str):
        return cls(["cmake", "--build"], presets)

    @classmethod
    def test(cls, presets: str):
        return cls(["ctest"], presets)

    @classmethod
    def pack(cls, presets: str):
        return cls(["cpack"], presets)


class CommandRunner:
    """"""

    def __init__(
        self,
        cwd: Path,
        output: StreamWriter,
        environment: Optional[Dict[str, Any]] = None,
    ):
        self.path = cwd
        self.output = output
        self.environment = environment

    def run(self, command: List["str"]) -> ReturnCode:
        self.output.write(f"exec: {shlex.join(command)}\n")
        return exec_subprocess(
            command,
            self.output,
            cwd=self.path,
            env=self.environment,
        )
