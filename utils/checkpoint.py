"""Checkpoint 读写。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def save_checkpoint(path: str, state: Dict[str, Any]) -> None:
    """保存当前状态到 JSON 文件。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint(path: str) -> Dict[str, Any]:
    """读取 checkpoint。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"checkpoint 不存在: {path}")
    return json.loads(p.read_text(encoding="utf-8"))
