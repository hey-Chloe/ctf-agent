"""命令执行器抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CommandResult:
    """命令执行结果。"""

    exit_code: int
    output: str
    error: str


class BaseExecutor(ABC):
    """命令执行器接口，Docker 和 SSH 都实现该接口。"""

    @abstractmethod
    def run(self, command: str, timeout: int | None = None) -> CommandResult:
        """执行命令。"""
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> None:
        """检查执行环境是否可用。"""
        raise NotImplementedError
