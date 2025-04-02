import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Callable

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


@dataclass
class ScriptParams(Params):
    path: Path

    def to_arguments(self) -> List[str]:
        arguments = ["-P", str(self.path)]
        return arguments


@dataclass
class PresetParams(Params):
    preset_name: str

    def to_arguments(self) -> List[str]:
        arguments = ["--presets", self.preset_name]
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
        use_presets: bool = False,
    ):
        self.path = Path(path)
        self.output = output
        self.environment = environment
        self.use_presets = use_presets

        self.source_path = Path(path, source_prefix).resolve()
        self.build_path = Path(path, build_prefix).resolve()

    def get_command_func(self, name: str) -> Callable[[Params, str], ReturnCode]:
        command_map = {
            "legacy": {
                "configure": self._configure,
                "build": self._build,
                "test": self._test,
            },
            "presets": {
                "configure": self._configure_with_presets,
                "build": self._build_with_presets,
                "test": self._test_with_presets,
            },
        }

        if self.use_presets:
            return command_map["presets"][name]
        return command_map["legacy"][name]

    def configure(self, params: Params, arguments: str = "") -> ReturnCode:
        return self.get_command_func("configure")(params, arguments)

    def build(self, params: Params, arguments: str = "") -> ReturnCode:
        return self.get_command_func("build")(params, arguments)

    def test(self, params: Params, arguments: str = "") -> ReturnCode:
        return self.get_command_func("test")(params, arguments)

    def run_script(self, params: Params, arguments: str = "") -> ReturnCode:
        return self._run_script(params, arguments)

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

    def _configure_with_presets(
        self, params: PresetParams, arguments: str = ""
    ) -> ReturnCode:
        command = [
            "cmake",
            f"-S{self.source_path.as_posix()}",
            f"-B{self.build_path.as_posix()}",
        ]
        command.extend(params.to_arguments())

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _build_with_presets(
        self, params: PresetParams, arguments: str = ""
    ) -> ReturnCode:
        command = ["cmake", "--build", self.build_path.as_posix()]
        command.extend(params.to_arguments())

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _test_with_presets(
        self, params: PresetParams, arguments: str = ""
    ) -> ReturnCode:
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

    def _run_script(self, params: ScriptParams, arguments: str = "") -> ReturnCode:
        command = [
            "cmake",
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
