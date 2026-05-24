import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(script_dir, "venv", "Scripts", "python.exe")
main_script = os.path.join(script_dir, "main.py")

subprocess.Popen(
    [venv_python, main_script],
    cwd=script_dir,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
