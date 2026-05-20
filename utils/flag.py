"""Flag 提取工具函数。"""

from __future__ import annotations

import re
from typing import List

# 覆盖常见 CTF flag 格式。可按比赛规则扩展。
FLAG_PATTERNS = [
    re.compile(r"flag\{[^\s{}]{1,200}\}", re.IGNORECASE),
    re.compile(r"ctf\{[^\s{}]{1,200}\}", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9_\-]{2,30}\{[^\s{}]{1,200}\}"),
]


def extract_flags(text: str) -> List[str]:
    """从文本中提取 flag 候选。"""
    found: list[str] = []
    for pattern in FLAG_PATTERNS:
        for match in pattern.findall(text or ""):
            if match not in found:
                found.append(match)
    return found
