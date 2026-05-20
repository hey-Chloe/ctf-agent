"""LLM 后端适配。"""

from __future__ import annotations

from typing import Any


def build_llm(llm_config: Any):
    """根据配置创建 LangChain ChatModel。

    支持：
    - openai：OpenAI API
    - deepseek：OpenAI 兼容接口
    - ollama：本地 Ollama
    """
    provider = llm_config.provider.lower().strip()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=llm_config.model,
            base_url=llm_config.api_base or "http://localhost:11434",
            temperature=llm_config.temperature,
        )

    if provider in {"openai", "deepseek"}:
        from langchain_openai import ChatOpenAI

        if not llm_config.api_key:
            raise ValueError(f"provider={provider} 需要在 config.json 中设置 llm.api_key。")
        kwargs = {
            "model": llm_config.model,
            "api_key": llm_config.api_key,
            "temperature": llm_config.temperature,
            "timeout": llm_config.timeout,
            "max_retries": llm_config.max_retries,
        }
        if llm_config.api_base:
            kwargs["base_url"] = llm_config.api_base
        return ChatOpenAI(**kwargs)

    raise ValueError(f"未知 LLM provider: {llm_config.provider}")


def message_to_text(message: Any) -> str:
    """兼容不同 LangChain 消息对象。"""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    return str(content)
