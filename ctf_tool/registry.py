"""工具注册表。"""

from __future__ import annotations

from typing import Dict

from ctf_tool.base import CtfBaseTool
from ctf_tool.command_tools import ContainerCommandTool, PythonExecutionTool
from ctf_tool.ctf_tools import (
    BinwalkTool,
    DirsearchTool,
    FileTypeTool,
    NmapTool,
    SqlmapTool,
    StegoTool,
    StringsTool,
)
from ctf_tool.submit_tool import FlagSubmitTool
from utils.executor import BaseExecutor


def build_default_tools(config, executor: BaseExecutor) -> Dict[str, CtfBaseTool]:
    """构建默认工具集合。"""
    tools = [
        ContainerCommandTool(executor),
        PythonExecutionTool(executor),
        NmapTool(executor),
        DirsearchTool(executor),
        SqlmapTool(executor),
        FileTypeTool(executor),
        BinwalkTool(executor),
        StringsTool(executor),
        StegoTool(executor),
        FlagSubmitTool(config.ctfd),
    ]
    return {tool.name: tool for tool in tools}
