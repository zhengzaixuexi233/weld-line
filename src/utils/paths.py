"""应用运行路径工具。"""

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """返回应用根目录，兼容源码运行和 PyInstaller 打包运行。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def app_path(*parts: str) -> Path:
    """返回应用根目录下的路径。"""
    return app_base_dir().joinpath(*parts)
