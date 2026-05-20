"""配置加载与数据模型。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class LlmConfig:
    provider: str = "ollama"
    model: str = "llama3.1"
    api_key: str = ""
    api_base: str = "http://localhost:11434"
    temperature: float = 0.1
    timeout: int = 120
    max_retries: int = 2


@dataclass
class ExecutorConfig:
    type: str = "docker"
    container_name: str = "ctf-target"
    workdir: str = "/work"
    default_timeout: int = 120
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_port: int = 22
    ssh_key_path: str = ""


@dataclass
class AgentConfig:
    max_steps: int = 30
    checkpoint_dir: str = "checkpoints"
    log_dir: str = "logs"
    debug: bool = False


@dataclass
class CtfdConfig:
    enabled: bool = False
    api_url: str = ""
    api_token: str = ""
    validate_ssl: bool = True


@dataclass
class AppConfig:
    llm: LlmConfig
    executor: ExecutorConfig
    agent: AgentConfig
    ctfd: CtfdConfig
    raw: Dict[str, Any]


def _section(data: Dict[str, Any], name: str) -> Dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def load_config(path: str = "config.json") -> AppConfig:
    """从 JSON 文件加载配置。"""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {path}。请复制 config_template.json 为 config.json 后修改。"
        )

    data = json.loads(config_path.read_text(encoding="utf-8"))
    llm = LlmConfig(**{**LlmConfig().__dict__, **_section(data, "llm")})
    executor = ExecutorConfig(**{**ExecutorConfig().__dict__, **_section(data, "executor")})
    agent = AgentConfig(**{**AgentConfig().__dict__, **_section(data, "agent")})
    ctfd = CtfdConfig(**{**CtfdConfig().__dict__, **_section(data, "ctfd")})
    return AppConfig(llm=llm, executor=executor, agent=agent, ctfd=ctfd, raw=data)
