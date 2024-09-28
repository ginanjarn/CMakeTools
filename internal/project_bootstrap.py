from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List


class ProjectType(Enum):
    """"""

    LIBRARY = "library"
    EXECUTABLE = "executable"


@dataclass
class Project:
    """"""

    name: str
    type: ProjectType
    path: Path
    files: List["File"]


@dataclass
class File:
    """"""

    path: Path
    text: str

    def save(self):
        """"""
        self.path.write_text(self.text)


class Bootstrap:
    """"""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)

    def generate(self, type: ProjectType, name: str) -> Project:
        return self._generate(ProjectType(type), name)

    def _generate(self, type: ProjectType, name: str) -> Project:
        files = []

        if cmakelists_file := self._generate_cmakelists_file(type, name):
            files.append(cmakelists_file)

        if header_file := self._generate_header_file(type, name):
            files.append(header_file)

        if source_file := self._generate_source_file(type, name):
            files.append(source_file)

        return Project(type, name, self.project_path, files)

    def _generate_cmakelists_file(self, type: ProjectType, name: str) -> File:
        cmake_min_version = "3.20"
        project_version = "0.1.0"
        lines = [
            f"cmake_minimum_required(VERSION {cmake_min_version})\n",
            "\n",
            f"project({name} VERSION {project_version})\n",
        ]

        if type == ProjectType.LIBRARY:
            lines.append(f"add_library({name} {name}.cpp {name}.hpp)\n")

        elif type == ProjectType.EXECUTABLE:
            lines.append(f"add_executable({name} main.cpp)\n")

        file_path = self.project_path.joinpath("CMakeLists.txt")
        return File(file_path, "".join(lines))

    def _generate_header_file(self, type: ProjectType, name: str) -> File:
        if type == ProjectType.LIBRARY:
            upper_name = name.upper()
            content = "void print_hello();"
            text = (
                f"#ifndef {upper_name}_H\n"
                f"#define {upper_name}_H\n"
                "\n"
                f"{content}\n"
                "\n"
                "#endif"
            )

            file_path = self.project_path.joinpath(f"{name}.hpp")
            return File(file_path, text)

        else:
            return None

    def _generate_source_file(self, type: ProjectType, name: str) -> File:
        if type == ProjectType.LIBRARY:
            text = (
                "#include <iostream>\n"
                f'#include "{name}.hpp"\n'
                "\n"
                "void print_hello(){\n"
                '\tstd::cout<<"hello\\n";\n'
                "}\n"
            )
            file_path = self.project_path.joinpath(f"{name}.cpp")
            return File(file_path, text)

        if type == ProjectType.EXECUTABLE:
            text = (
                "#include <iostream>\n"
                "\n"
                "int main(int argc, char const *argv[]){\n"
                '\tstd::cout<<"hello\\n";\n'
                "}\n"
            )
            file_path = self.project_path.joinpath("main.cpp")
            return File(file_path, text)
