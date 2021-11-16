"""commands"""

import glob
import os
import re
import subprocess


class CMakeProjectType:
    EXECUTABLE = "executable"
    LIBRARY = "library"


template = (
    "cmake_minimum_required(VERSION {cmake_min_version})\n"
    "project({project_name} VERSION {project_version})\n"
    "\n"
    "include(CTest)\n"
    "enable_testing()\n"
    "\n"
    "add_library({project_name} {main_source})\n"
    "\n"
    "set(CPACK_PROJECT_NAME ${{PROJECT_NAME}})\n"
    "set(CPACK_PROJECT_VERSION ${{PROJECT_VERSION}})\n"
    "include(CPack)\n"
)

_STARTUPINFO = None
if os.name == "nt":
    # STARTUPINFO only available on windows
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW


def _cmake_version() -> str:
    try:
        proc = subprocess.Popen(
            ["cmake", "--version"],
            env=os.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=_STARTUPINFO,
        )
        sout, _ = proc.communicate()

        output = sout.decode()
        match = re.match(r"cmake version (\d+\.\d+\.\d+)", output)
        if not match:
            raise ValueError("unable to parse cmake version from '%s'" % output)

    except FileNotFoundError as err:
        raise ValueError("unable run 'cmake'") from err

    else:
        return match.group(1)


def _cmake_path():
    where_cmd = "where" if os.name == "nt" else "which"
    try:
        proc = subprocess.Popen(
            [where_cmd, "cmake"],
            env=os.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=_STARTUPINFO,
        )
        sout, _ = proc.communicate()
    except Exception:
        return None
    else:
        if not sout:
            return None
        return sout.decode().strip()


def cmake_path():
    return _cmake_path()


def _msvc_path():
    where_cmd = "where" if os.name == "nt" else "which"
    try:
        proc = subprocess.Popen(
            [where_cmd, "cl"],
            env=os.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=_STARTUPINFO,
        )
        sout, _ = proc.communicate()
    except Exception:
        return None
    else:
        if not sout:
            return None
        return sout.decode().strip()


def _clang_path():
    where_cmd = "where" if os.name == "nt" else "which"
    try:
        proc = subprocess.Popen(
            [where_cmd, "clang"],
            env=os.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=_STARTUPINFO,
        )
        sout, _ = proc.communicate()
    except Exception:
        return None
    else:
        if not sout:
            return None
        return sout.decode().strip()


def _gcc_path():
    where_cmd = "where" if os.name == "nt" else "which"
    try:
        proc = subprocess.Popen(
            [where_cmd, "gcc"],
            env=os.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=_STARTUPINFO,
        )
        sout, _ = proc.communicate()
    except Exception:
        return None
    else:
        if not sout:
            return None

        gccpath = sout.decode().strip()
        if os.name == "nt":
            gccdir = os.path.dirname(gccpath)
            return max(glob.glob(gccdir + "/*mingw32-gcc.exe"))

        return gccpath


def _cxx_path(cc_path: str):
    return cc_path.replace("clang", "clang++").replace("gcc", "g++")


def bootstrap_cmakelist(
    project_path: str,
    project_name: str,
    project_type: str,
    project_version: str = "0.1.0",
    cmake_min_version: str = "",
):
    """generate CMakeLists.txt file

    - project_path: project path where locate CMakeLists.txt
    - project_name
    - project_type: valid type = [ 'executable', 'library' ]
    - project_version
    - cmake_min_version
    """

    main_source = ""
    if project_type == CMakeProjectType.EXECUTABLE:
        main_source = "main.cpp"
    elif project_type == CMakeProjectType.LIBRARY:
        main_source = "{project_name}.cpp".format(project_name=project_name)

    if not cmake_min_version:
        cmake_version = _cmake_version().split(".")
        cmake_min_version = "{major}.0.0".format(major=cmake_version[0])

    fields = {
        "project_name": project_name,
        "main_source": main_source,
        "project_version": project_version,
        "cmake_min_version": cmake_min_version,
    }

    cmakelists_content = template.format(**fields)

    # bootstrap main source code
    main_source_path = os.path.join(project_path, main_source)
    with open(main_source_path, "w") as file:
        pass

    file_path = os.path.join(project_path, "CMakeLists.txt")
    with open(file_path, "w") as file:
        file.write(cmakelists_content)


def get_compiler_list():
    compilers = []

    msvc = _msvc_path()
    if msvc:
        compilers.append(msvc)
    clang = _clang_path()
    if clang:
        compilers.append(clang)
    gcc = _gcc_path()
    if gcc:
        compilers.append(gcc)

    return compilers


def generate_cmake(
    project_path: str, *, cmake_path: str, c_compiler: str, build_generator: str
) -> None:
    """generate cmake"""

    project_path = os.path.abspath(project_path)
    fields = {
        "project_path": project_path.replace("\\", "/"),  # cmake use slash
        "c_compiler": c_compiler,
        "cxx_compiler": _cxx_path(c_compiler),
        "build_generator": build_generator,
    }
    commands = [
        cmake_path,
        "--no-warn-unused-cli",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE",
        "-DCMAKE_BUILD_TYPE:STRING=Debug",
        "-DCMAKE_C_COMPILER:FILEPATH={c_compiler}".format(**fields),
        "-DCMAKE_CXX_COMPILER:FILEPATH={cxx_compiler}".format(**fields),
        "-H{project_path}".format(**fields),
        "-B{project_path}/build".format(**fields),
    ]
    # use custom build generator
    if build_generator:
        commands.append("-G")
        commands.append(build_generator)

    proc = subprocess.Popen(
        commands,
        env=os.environ,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=_STARTUPINFO,
    )
    _, serr = proc.communicate()

    if serr:
        serr = serr.replace("\r\n", "\n")
        raise ValueError("Error generate_cmake:\n\n%s" % serr.decode())

    return None


def auto_generate_cmake(project_path: str):
    """auto generate use gcc and makefiles"""

    gcc = _gcc_path()
    builder = "MinGW Makefiles" if os.name == "nt" else ""
    generate_cmake(
        project_path, cmake_path="cmake", c_compiler=gcc, build_generator=builder
    )
