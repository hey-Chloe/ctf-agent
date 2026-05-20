"""SSH 执行器。

该执行器适合把命令发到远程靶场或远程分析容器。默认项目使用 DockerExecutor。
"""

from __future__ import annotations

import subprocess

from utils.executor import BaseExecutor, CommandResult


class SshExecutor(BaseExecutor):
    """基于系统 ssh 命令的远程执行器。"""

    def __init__(
        self,
        host: str,
        user: str,
        port: int = 22,
        key_path: str = "",
        default_timeout: int = 120,
    ):
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.default_timeout = default_timeout

    def healthcheck(self) -> None:
        if not self.host or not self.user:
            raise RuntimeError("SSH host/user 未配置。")

    def run(self, command: str, timeout: int | None = None) -> CommandResult:
        try:
            self.healthcheck()
            target = f"{self.user}@{self.host}"
            cmd = ["ssh", "-p", str(self.port), "-o", "BatchMode=yes"]
            if self.key_path:
                cmd.extend(["-i", self.key_path])
            cmd.extend([target, command])
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.default_timeout,
                check=False,
            )
            return CommandResult(completed.returncode, completed.stdout, completed.stderr)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return CommandResult(124, stdout, f"SSH 命令超时: {stderr}")
        except Exception as exc:  # noqa: BLE001
            return CommandResult(1, "", f"SSH 执行失败: {exc}")
