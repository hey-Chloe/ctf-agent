"""ReAct 提示词模板。

本项目采用 JSON 形式的 ReAct 输出，避免解析自由文本时出现歧义。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from ctf_tool.base import CtfBaseTool


def _truncate(text: str, limit: int = 3000) -> str:
    """截断过长文本，避免提示词无限增长。"""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[已截断，原始长度 {len(text)} 字符]"


def format_tools(tools: Iterable[CtfBaseTool]) -> str:
    """将工具列表格式化为 LLM 容易理解的 JSON。"""
    tool_items = []
    for tool in tools:
        try:
            schema = tool.args_schema.model_json_schema()
        except Exception:  # pragma: no cover - 兼容极端 Pydantic 场景
            schema = {}
        tool_items.append(
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": schema,
            }
        )
    return json.dumps(tool_items, ensure_ascii=False, indent=2)


def format_history(history: List[Dict[str, Any]], limit: int = 12) -> str:
    """将最近若干步历史格式化进上下文。"""
    if not history:
        return "暂无历史。"

    tail = history[-limit:]
    lines = []
    for item in tail:
        lines.append(
            json.dumps(
                {
                    "step": item.get("step"),
                    "thought": _truncate(str(item.get("thought", "")), 800),
                    "action": item.get("action"),
                    "action_input": item.get("action_input", {}),
                    "observation": _truncate(str(item.get("observation", "")), 2000),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines)


def build_react_prompt(
    challenge: Dict[str, Any],
    tools: Iterable[CtfBaseTool],
    history: List[Dict[str, Any]],
    flag_candidates: List[str],
    step: int,
    max_steps: int,
) -> str:
    """构建单轮思考提示词。"""
    challenge_text = json.dumps(challenge, ensure_ascii=False, indent=2)
    tools_text = format_tools(tools)
    history_text = format_history(history)
    flags_text = json.dumps(flag_candidates, ensure_ascii=False)

    return f"""
你是一个用于授权 CTF 靶场和比赛环境的自动化解题 Agent。你必须遵守以下规则：
1. 只针对用户提供的 CTF 题目、授权靶场 URL、附件或本地 Docker 容器进行分析。
2. 所有命令执行必须依赖工具系统，工具默认在隔离容器中运行。
3. 每轮只能选择一个 action；拿到 observation 后再继续下一轮。
4. 若已经确定 flag，请使用 final_answer 结束；若需要提交，请先调用 submit_flag 工具。
5. 优先采取可验证、低破坏性的动作；不要执行破坏系统或越权扩散的命令。
6. 输出必须是严格 JSON，不要输出 Markdown、注释或额外解释。

当前进度：第 {step + 1} / {max_steps} 步。

题目信息：
{challenge_text}

已发现的 Flag 候选：
{flags_text}

可用工具列表：
{tools_text}

最近历史：
{history_text}

请输出以下 JSON 结构之一：

继续调用工具：
{{
  "thought": "简要说明下一步推理，不要写过长内心独白",
  "action": "工具名称",
  "action_input": {{"参数名": "参数值"}},
  "final_answer": null
}}

结束解题：
{{
  "thought": "简要说明为什么结束",
  "action": "final_answer",
  "action_input": {{}},
  "final_answer": "最终 flag 或解题结论"
}}
""".strip()
