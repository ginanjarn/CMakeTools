import threading
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path

import sublime
import sublime_plugin

from .internal.project_bootstrap import Bootstrap, Project, ProjectType


def wait_event(event: threading.Event, function_call: object):
    """wait until event is set"""
    event.clear()
    function_call
    event.wait()


def set_event(event: threading.Event):
    """set event on done"""

    def func_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            finally:
                event.set()

        return wrapper

    return func_wrapper


class ProjectBuilder(ABC):
    task = ""

    def __init__(self, window: sublime.Window, project: Project) -> None:
        self.window = window
        self.project = project

    @abstractmethod
    def prompt_input(self) -> bool:
        """Prompt user input.
        Return False if invalid.
        """


class SelectPath(ProjectBuilder):
    task = "select path"

    def prompt_input(self) -> bool:
        if (path := Path(self._select_project_path())) and path.is_dir():
            self.project.path = path
            return True
        return False

    def _select_project_path(self) -> str:
        folders = self.window.folders()
        event = threading.Event()
        selected_path = ""

        @set_event(event)
        def select_folder(index):
            if index < 0:
                return

            nonlocal selected_path
            selected_path = folders[index]

        wait_event(
            event,
            self.window.show_quick_panel(folders, on_select=select_folder),
        )
        return selected_path


class SelectType(ProjectBuilder):
    task = "select type"

    def prompt_input(self) -> bool:
        if tp := self._select_project_type():
            self.project.type = tp
            return True
        return False

    def _select_project_type(self) -> str:
        types = [t.value for t in ProjectType]
        event = threading.Event()
        selected_type = None

        @set_event(event)
        def select_types(index):
            if index < 0:
                return

            nonlocal selected_type
            selected_type = types[index]

        wait_event(
            event,
            self.window.show_quick_panel(types, on_select=select_types),
        )
        return selected_type


class InputName(ProjectBuilder):
    task = "input name"

    def prompt_input(self) -> bool:
        if name := self._input_project_name():
            self.project.name = name
            return True
        return False

    def _input_project_name(self):
        input_name = ""
        event = threading.Event()

        @set_event(event)
        def set_project_name(text):
            if not text:
                return
            nonlocal input_name
            input_name = text

        wait_event(
            event,
            self.window.show_input_panel(
                "Project name",
                initial_text="awesome_project",
                on_done=set_project_name,
                on_change=None,
                on_cancel=None,
            ),
        )
        return input_name


class CmaketoolsQuickstartCommand(sublime_plugin.WindowCommand):
    """"""

    def run(self):
        thread = threading.Thread(target=self._run)
        thread.start()

    def _run(self):
        project = Project("", None, None, None)

        input_flow = [SelectPath, SelectType, InputName]
        for cls in input_flow:
            prompt = cls(self.window, project)
            ok = prompt.prompt_input()
            if not ok:
                print(f"task incomplete: {prompt.task}")
                return

        bootstrapper = Bootstrap(project.path)
        project = bootstrapper.generate(project.type, project.name)

        for file in project.files:
            file.save()
