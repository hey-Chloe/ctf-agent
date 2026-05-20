"""日志配置。"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path


def setup_logging(log_dir: str = "logs", debug: bool = False) -> str:
    """同时输出日志到控制台和文件。"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = str(Path(log_dir) / f"ctf_agent_{time.strftime('%Y%m%d_%H%M%S')}.log")
    level = logging.DEBUG if debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    root.addHandler(console)
    root.addHandler(file_handler)
    return log_file
