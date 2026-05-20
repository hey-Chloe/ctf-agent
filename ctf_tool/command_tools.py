"""通用命令和 Python 执行工具。"""

from __future__ import annotations

import base64
import shlex
from typing import Any

from pydantic import BaseModel, Field

from ctf_tool.base import CtfBaseTool, ToolResult
from utils.executor import BaseExecutor


class CommandArgs(BaseModel):
    """容器命令执行参数。"""

    command: str = Field(..., description="需要在 ctf-target 容器内执行的 shell 命令")
    timeout: int | None = Field(default=None, description="超时时间，单位秒；不传则使用默认值")


class ContainerCommandTool(CtfBaseTool):
    """在隔离容器中执行命令。"""

    name = "run_command"
    description = "在预配置 Docker 容器 ctf-target 内执行 shell 命令。适合 nc、curl、grep、cat 等通用操作。"
    args_schema = CommandArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        result = self.executor.run(args.command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class PythonCodeArgs(BaseModel):
    """Python 代码执行参数。"""

    code: str = Field(..., description="需要执行的 Python 代码。代码将在容器内通过 python3 运行。")
    timeout: int | None = Field(default=None, description="超时时间，单位秒")


class PythonExecutionTool(CtfBaseTool):
    """在容器内执行 Python 代码。"""

    name = "run_python"
    description = "在 ctf-target 容器内执行短 Python 脚本，适合解码、爆破小搜索空间、处理附件。"
    args_schema = PythonCodeArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        encoded = base64.b64encode(args.code.encode("utf-8")).decode("ascii")
        # 使用 base64 避免引号、换行和 EOF 冲突。
        command = (
            "python3 - <<'PY'\n"
            "import base64\n"
            f"code = base64.b64decode({shlex.quote(encoded)}).decode('utf-8')\n"
            "exec(compile(code, '<ctf-agent-python>', 'exec'))\n"
            "PY"
        )
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)
