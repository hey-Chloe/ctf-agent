"""Agent 状态定义。

这里尽量保持状态为 JSON 可序列化对象，方便随时写入 checkpoints/ 并在中断后恢复。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class HistoryItem(TypedDict, total=False):
    """单步 ReAct 历史记录。"""

    step: int
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: Optional[str]
    raw_response: str


class AgentState(TypedDict, total=False):
    """LangGraph 在各节点之间传递的状态。"""

    challenge: Dict[str, Any]
    history: List[HistoryItem]
    step: int
    max_steps: int
    finished: bool
    final_answer: Optional[str]
    flag_candidates: List[str]
    checkpoint_file: str
    error: Optional[str]
