import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any

from .subprocess_helper import exec_subprocess, StreamWriter, ReturnCode


CMakeCacheEntry = Dict[str, Any]


class Params(ABC):
    """"""

    @abstractmethod
    def to_arguments(self) -> List[str]:
        """"""


@dataclass
class ConfigureParams(Params):
    generator: str = ""
    cache_entry: CMakeCacheEntry = None

    def to_arguments(self) -> List[str]:
        arguments = []
        if self.generator:
            arguments.append(f"-G{shlex.quote(self.generator)}")

        if self.cache_entry:
            for var, value in self.cache_entry.items():
                arguments.append(f"-D{var}={shlex.quote(str(value))}")

        return arguments


@dataclass
class BuildParams(Params):
    target: str = "all"

    def to_arguments(self) -> List[str]:
        return ["--target", self.target]


@dataclass
class TestParams(Params):
    regex: str = ""

    def to_arguments(self) -> List[str]:
        arguments = []
        if self.regex:
            arguments.append(f"-R{self.regex}")

        return arguments


class Project:
    """"""

    def __init__(
        self,
        path: Path,
        output: StreamWriter,
        *,
        source_prefix: str = "",
        build_prefix: str = "build",
        environment: dict = None,
    ):
        self.path = Path(path)
        self.output = output
        self.environment = environment

        self.source_path = Path(path, source_prefix).resolve()
        self.build_path = Path(path, build_prefix).resolve()

    def configure(self, params: ConfigureParams, arguments: str = "") -> ReturnCode:
        return self._configure(params, arguments)

    def build(self, params: BuildParams, arguments: str = "") -> ReturnCode:
        return self._build(params, arguments)

    def test(self, params: TestParams, arguments: str = "") -> ReturnCode:
        return self._test(params, arguments)

    def _configure(self, params: ConfigureParams, arguments: str = "") -> ReturnCode:
        command = [
            "cmake",
            f"-S{self.source_path.as_posix()}",
            f"-B{self.build_path.as_posix()}",
        ]
        command.extend(params.to_arguments())

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _build(self, params: BuildParams, arguments: str = "") -> ReturnCode:
        command = ["cmake", "--build", self.build_path.as_posix()]
        command.extend(params.to_arguments())

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _test(self, params: TestParams, arguments: str = "") -> ReturnCode:
        command = [
            "ctest",
            "--test-dir",
            self.build_path.as_posix(),
            "--output-on-failure",
        ]
        command.extend(params.to_arguments())

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def run_command(self, command: List["str"]) -> ReturnCode:
        self.output.write(f"exec: {shlex.join(command)}\n")
        return exec_subprocess(
            command,
            self.output,
            cwd=self.path,
            env=self.environment,
        )
