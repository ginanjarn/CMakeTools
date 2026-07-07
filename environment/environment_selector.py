import json
import os
import subprocess
from pathlib import Path
from typing import Optional
import sublime
import sublime_plugin

TARGET_LANGUAGE = ["C", "C++", "CMake"]


class CmaketoolsSelectEnvironmentCommand(sublime_plugin.WindowCommand):

    def run(self):
        home = str(Path.home())
        script_extension = ["bat", "ps1"] if os.name == "nt" else ["sh"]
        allowed = [
            ("Activation script", script_extension),
        ]
        try:
            sublime.open_dialog(self.run_script, file_types=allowed, directory=home)
        except AttributeError:
            print("Unable select environment script")

    def run_script(self, path: str) -> Optional[dict]:
        if not path:
            return

        command_map = {
            ".bat": f'%WINDIR%\\System32\\cmd.exe /c "call {path} && set"',
            ".ps1": f'%WINDIR%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -ExecutionPolicy ByPass -Command "{path}; Get-ChildItem Env: | ConvertTo-Json"',
            ".sh": f"/bin/bash -c {path} && env",
        }
        suffix = Path(path).suffix
        command = command_map[suffix]

        ret = subprocess.run(
            command,
            capture_output=True,
            universal_newlines=True,
            shell=True,
        )
        if ret.returncode != 0:
            print(ret.stderr)
            return

        if suffix == ".ps1":
            # powershell json
            itens = json.loads(ret.stdout)
            envs = {item["Name"].upper(): item["Value"] for item in itens}
        else:
            items = [line.split("=") for line in ret.stdout.splitlines() if line]
            envs = {k.upper(): v for k, v in items}

        if not envs:
            return

        # normalize envs key
        norm_envs = {k.upper(): v for k, v in envs.items()}

        for lang in TARGET_LANGUAGE:
            self.save_envs_settings(f"{lang}.sublime-settings", norm_envs)

        # load kit from selected environment
        self.window.run_command("cmaketools_set_kits")

    def save_envs_settings(self, base_name: str, value: dict) -> None:
        settings = sublime.load_settings(base_name)
        settings.set("envs", value)
        sublime.save_settings(base_name)
