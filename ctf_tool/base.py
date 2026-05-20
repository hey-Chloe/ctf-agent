"""统一工具基类。

所有工具都继承 CtfBaseTool，并提供：
- name：工具名称，LLM 通过该名称调用工具。
- description：自然语言说明，帮助 LLM 判断何时使用。
- args_schema：Pydantic 参数模型，描述工具参数。
- run：真正执行工具逻辑。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果。"""

    ok: bool = Field(description="工具是否执行成功")
    output: str = Field(default="", description="标准输出或主要结果")
    error: str | None = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    def to_observation(self, max_chars: int = 12000) -> str:
        """转为 ReAct observation 文本，并限制长度。"""
        parts = [f"ok: {self.ok}"]
        if self.output:
            parts.append("output:\n" + self.output)
        if self.error:
            parts.append("error:\n" + self.error)
        if self.metadata:
            parts.append("metadata:\n" + str(self.metadata))
        text = "\n\n".join(parts)
        if len(text) > max_chars:
            return text[:max_chars] + f"\n...[观察结果已截断，原始长度 {len(text)} 字符]"
        return text


class EmptyArgs(BaseModel):
    """无参数工具的占位 schema。"""


class CtfBaseTool(ABC):
    """CTF 工具抽象基类。"""

    name: str
    description: str
    args_schema: Type[BaseModel] = EmptyArgs

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """执行工具并返回 ToolResult。"""
        raise NotImplementedError

    def as_langchain_tool(self) -> StructuredTool:
        """转换为 LangChain StructuredTool，便于后续扩展到工具调用模型。"""
        return StructuredTool.from_function(
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
            func=lambda **kwargs: self.run(**kwargs).model_dump(),
        )
