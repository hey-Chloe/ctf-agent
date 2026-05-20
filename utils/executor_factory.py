"""执行器工厂。"""

from __future__ import annotations

from utils.docker_client import DockerExecutor
from utils.executor import BaseExecutor
from utils.ssh_client import SshExecutor


def build_executor(config) -> BaseExecutor:
    """根据配置创建 Docker 或 SSH 执行器。"""
    executor_type = config.executor.type.lower().strip()
    if executor_type == "ssh":
        return SshExecutor(
            host=config.executor.ssh_host,
            user=config.executor.ssh_user,
            port=config.executor.ssh_port,
            key_path=config.executor.ssh_key_path,
            default_timeout=config.executor.default_timeout,
        )
    if executor_type == "docker":
        return DockerExecutor(
            container_name=config.executor.container_name,
            workdir=config.executor.workdir,
            default_timeout=config.executor.default_timeout,
        )
    raise ValueError(f"未知 executor.type: {config.executor.type}")
