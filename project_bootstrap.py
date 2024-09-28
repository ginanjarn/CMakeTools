import threading
from functools import wraps

import sublime_plugin

from .internal import project_bootstrap


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


class CmaketoolsQuickstartCommand(sublime_plugin.WindowCommand):
    """"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_path = ""
        self.project_type = ""
        self.project_name = ""

        self.event = threading.Event()

    def run(self):
        thread = threading.Thread(target=self._run)
        thread.start()

    def _run(self):
        self._select_project_path()
        if not self.project_path:
            return

        self._select_project_type()
        if not self.project_type:
            return

        self._input_project_name()
        if not self.project_name:
            return

        bootstrapper = project_bootstrap.Bootstrap(self.project_path)
        project = bootstrapper.generate(self.project_type, self.project_name)

        for file in project.files:
            file.save()

    def _select_project_path(self):
        folders = self.window.folders()

        @set_event(self.event)
        def select_folder(index):
            if index < 0:
                return
            self.project_path = folders[index]

        wait_event(
            self.event,
            self.window.show_quick_panel(folders, on_select=select_folder),
        )

    def _select_project_type(self):
        types = ["executable", "library"]

        @set_event(self.event)
        def select_types(index):
            if index < 0:
                return
            self.project_type = types[index]

        wait_event(
            self.event,
            self.window.show_quick_panel(types, on_select=select_types),
        )

    def _input_project_name(self):
        @set_event(self.event)
        def set_project_name(text):
            if not text:
                return
            self.project_name = text

        wait_event(
            self.event,
            self.window.show_input_panel(
                "Project name",
                initial_text="awesome_project",
                on_done=set_project_name,
                on_change=None,
                on_cancel=None,
            ),
        )
