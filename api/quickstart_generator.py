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


def generate_quickstart(
    workspace_path: PathStr, project_type: ProjectTypeStr, project_name: str
):
    # fmt: off
    template_map = {
        "Executable": {
            "cmake_template": executable_cmake_template % {"project_name": project_name},
            "source_template": executable_cpp_template ,
        },
        "Library": {
            "cmake_template": library_cmake_template % {"project_name": project_name},
            "source_template": library_cpp_template % {"project_name": project_name},
        },
    }
    # fmt: on

    if project_type not in template_map:
        raise ValueError(f"unable generate quickstart for type {project_type!r}")

    template = template_map[project_type]

    cmake_path = Path(workspace_path).joinpath("CMakeLists.txt")
    if not cmake_path.exists():
        cmake_path.write_text(template["cmake_template"])

    source_filename = f"{project_name}.cpp" if project_type == "Library" else "main.cpp"
    source_path = Path(workspace_path).joinpath(source_filename)
    if not source_path.exists():
        source_path.write_text(template["source_template"])
