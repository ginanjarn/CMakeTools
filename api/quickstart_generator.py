"""cmake quickstart generator helper"""

from pathlib import Path

executable_cmake_template = """\
cmake_minimum_required(VERSION 3.20.0)
project(%(project_name)s VERSION 0.1.0)

include(CTest)
enable_testing()

add_executable(%(project_name)s main.cpp)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
"""

executable_cpp_template = """\
#include <iostream>

int main(int argc, char const *argv[])
{
  std::cout<<"hello world";
  return 0;
}
"""

library_cmake_template = """\
cmake_minimum_required(VERSION 3.20.0)
project(%(project_name)s VERSION 0.1.0)

include(CTest)
enable_testing()

add_library(%(project_name)s %(project_name)s.cpp)

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)
"""

library_cpp_template = """\
#include <iostream>

void say_hello(){
    std::cout << "Hello, from %(project_name)s!";
}
"""

PathStr = str
ProjectTypeStr = str

PROJECT_TYPES = ["Executable", "Library"]


def generate_executable(workspace_path: PathStr, project_name: str):
    workspace_path = Path(workspace_path)

    if (path := workspace_path.joinpath("CMakeLists.txt")) and not path.exists():
        path.write_text(executable_cmake_template % {"project_name": project_name})

    if (path := workspace_path.joinpath("main.cpp")) and not path.exists():
        path.write_text(executable_cpp_template)


def generate_library(workspace_path: PathStr, project_name: str):
    workspace_path = Path(workspace_path)

    if (path := workspace_path.joinpath("CMakeLists.txt")) and not path.exists():
        path.write_text(library_cmake_template % {"project_name": project_name})

    if (path := workspace_path.joinpath(f"{project_name}.cpp")) and not path.exists():
        path.write_text(library_cpp_template % {"project_name": project_name})


def generate_quickstart(
    workspace_path: PathStr, project_type: ProjectTypeStr, project_name: str
):
    if project_type == "Executable":
        generate_executable(workspace_path, project_name)

    elif project_type == "Library":
        generate_library(workspace_path, project_name)

    else:
        raise ValueError(f"unable generate quickstart for type {project_type!r}")
