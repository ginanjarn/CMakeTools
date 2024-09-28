import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Any

from .subprocess_helper import exec_subprocess, StreamWriter, ReturnCode


CMakeCacheEntry = Dict[str, Any]


@dataclass
class ConfigureParams:
    generator: str = ""
    cache_entry: CMakeCacheEntry = None


@dataclass
class BuildParams:
    target: str = "all"
    preset: Path = None


@dataclass
class TestParams:
    regex: str = ""


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

        self.source_path = self.path.joinpath(source_prefix)
        self.build_path = self.path.joinpath(build_prefix)

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
        if entry := params.cache_entry:
            command.extend(self._translate_cache_entry(entry))

        if generator := params.generator:
            command.append(f"-G{generator}")

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _build(self, params: BuildParams, arguments: str = "") -> ReturnCode:
        command = ["cmake", "--build", self.build_path.as_posix()]

        if target := params.target:
            command.extend(["--target", target])

        if preset := params.preset:
            command.extend(["--preset", preset])

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

        if regex := params.regex:
            command.append(f"-R{regex}")

        if arguments:
            command += shlex.split(arguments)

        return self.run_command(command)

    def _translate_cache_entry(self, entry: CMakeCacheEntry) -> Iterator[str]:
        for key, value in entry.items():
            yield f"-D{key}={shlex.quote(str(value))}"

    def run_command(self, command: List["str"]) -> ReturnCode:
        self.output.write(f"exec: {shlex.join(command)}\n")
        return exec_subprocess(
            command,
            self.output,
            cwd=self.path,
            env=self.environment,
        )
