"""Docker 容器执行封装。"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from utils.executor import BaseExecutor, CommandResult

LOGGER = logging.getLogger(__name__)


class DockerExecutor(BaseExecutor):
    """通过 Docker 容器执行命令。

    使用 Docker SDK 检查容器状态，使用 docker exec 执行命令，以便利用 subprocess timeout。
    """

    def __init__(self, container_name: str = "ctf-target", workdir: str = "/work", default_timeout: int = 120):
        self.container_name = container_name
        self.workdir = workdir
        self.default_timeout = default_timeout

    def healthcheck(self) -> None:
        """确认 Docker 可用且容器正在运行。"""
        try:
            import docker  # 延迟导入，便于在未安装依赖时给出清晰错误

            client = docker.from_env()
            container = client.containers.get(self.container_name)
            container.reload()
            if container.status != "running":
                raise RuntimeError(f"容器 {self.container_name} 状态为 {container.status}，请先启动。")
        except ImportError as exc:
            raise RuntimeError("未安装 docker Python SDK，请执行 pip install docker。") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Docker 环境检查失败: {exc}") from exc

    def run(self, command: str, timeout: int | None = None) -> CommandResult:
        """在容器中执行 shell 命令。"""
        try:
            self.healthcheck()
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=127, output="", error=str(exc))

        cmd = [
            "docker",
            "exec",
            "-w",
            self.workdir,
            self.container_name,
            "bash",
            "-lc",
            command,
        ]
        LOGGER.debug("Docker exec: %s", command)
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.default_timeout,
                check=False,
            )
            return CommandResult(
                exit_code=completed.returncode,
                output=completed.stdout,
                error=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return CommandResult(exit_code=124, output=stdout, error=f"命令超时: {stderr}")
        except FileNotFoundError:
            return CommandResult(exit_code=127, output="", error="未找到 docker CLI，请安装 Docker 并确保 docker 在 PATH 中。")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(exit_code=1, output="", error=f"命令执行异常: {exc}")
