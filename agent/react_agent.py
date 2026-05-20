"""基于 LangGraph 的 ReAct Agent 主体。"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from agent.prompts import build_react_prompt
from agent.state import AgentState
from ctf_tool.base import CtfBaseTool, ToolResult
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.flag import extract_flags
from utils.llm import build_llm, message_to_text

LOGGER = logging.getLogger(__name__)


class CtfReactAgent:
    """CTF 自动化解题 Agent。

    设计要点：
    - 使用 LangGraph 将“思考节点”和“行动节点”连接成状态机。
    - LLM 只负责输出结构化 JSON 决策。
    - 工具执行结果写回状态，并随时保存 checkpoint。
    """

    def __init__(self, config: Any, tools: Mapping[str, CtfBaseTool]):
        self.config = config
        self.tools = dict(tools)
        self.llm = build_llm(config.llm)
        self.graph = self._build_graph()

    def _build_graph(self):
        """构建 LangGraph 状态机。"""
        workflow = StateGraph(AgentState)
        workflow.add_node("think", self._think_node)
        workflow.add_node("act", self._act_node)
        workflow.set_entry_point("think")
        workflow.add_conditional_edges(
            "think",
            self._route_after_think,
            {"act": "act", "end": END},
        )
        workflow.add_conditional_edges(
            "act",
            self._route_after_act,
            {"think": "think", "end": END},
        )
        return workflow.compile()

    def run(
        self,
        challenge: Optional[Dict[str, Any]] = None,
        resume_checkpoint: Optional[str] = None,
        max_steps: Optional[int] = None,
    ) -> AgentState:
        """启动或恢复一次解题流程。"""
        if resume_checkpoint:
            state = load_checkpoint(resume_checkpoint)
            LOGGER.info("已从存档恢复: %s", resume_checkpoint)
        else:
            if not challenge:
                raise ValueError("challenge 不能为空，除非使用 resume_checkpoint。")
            state = self._new_state(challenge, max_steps=max_steps)

        recursion_limit = int(state.get("max_steps", 30)) * 3 + 10
        final_state = self.graph.invoke(state, config={"recursion_limit": recursion_limit})
        return final_state

    def _new_state(self, challenge: Dict[str, Any], max_steps: Optional[int] = None) -> AgentState:
        """创建新的初始状态。"""
        checkpoint_dir = Path(self.config.agent.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = checkpoint_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
        return AgentState(
            challenge=challenge,
            history=[],
            step=0,
            max_steps=int(max_steps or self.config.agent.max_steps),
            finished=False,
            final_answer=None,
            flag_candidates=[],
            checkpoint_file=str(checkpoint_file),
            error=None,
        )

    def _think_node(self, state: AgentState) -> AgentState:
        """LLM 思考节点：根据题目和历史选择下一个动作。"""
        step = int(state.get("step", 0))
        max_steps = int(state.get("max_steps", self.config.agent.max_steps))
        if step >= max_steps:
            state["finished"] = True
            state["final_answer"] = state.get("final_answer") or "达到最大步数限制，自动停止。"
            save_checkpoint(state["checkpoint_file"], state)
            return state

        prompt = build_react_prompt(
            challenge=state.get("challenge", {}),
            tools=self.tools.values(),
            history=state.get("history", []),
            flag_candidates=state.get("flag_candidates", []),
            step=step,
            max_steps=max_steps,
        )

        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content="你是 CTF ReAct Agent 的决策模型，只输出严格 JSON。"),
                    HumanMessage(content=prompt),
                ]
            )
            raw_text = message_to_text(response)
        except Exception as exc:  # noqa: BLE001 - 需要把 LLM 异常写进日志和 checkpoint
            LOGGER.exception("LLM 调用失败")
            state["finished"] = True
            state["error"] = f"LLM 调用失败: {exc}"
            state["final_answer"] = state["error"]
            save_checkpoint(state["checkpoint_file"], state)
            return state

        try:
            decision = self._parse_llm_json(raw_text)
        except ValueError as exc:
            LOGGER.warning("LLM 输出无法解析，将作为观察写入后停止: %s", raw_text)
            state["finished"] = True
            state["error"] = str(exc)
            state["final_answer"] = f"LLM 输出无法解析: {raw_text}"
            save_checkpoint(state["checkpoint_file"], state)
            return state

        action = str(decision.get("action", "")).strip()
        action_input = decision.get("action_input") or {}
        if not isinstance(action_input, dict):
            action_input = {"value": action_input}

        item = {
            "step": step + 1,
            "thought": str(decision.get("thought", "")),
            "action": action,
            "action_input": action_input,
            "observation": None,
            "raw_response": raw_text,
        }
        history = list(state.get("history", []))
        history.append(item)
        state["history"] = history
        state["step"] = step + 1

        LOGGER.info("[Step %s] Thought: %s", step + 1, item["thought"])
        LOGGER.info("[Step %s] Action: %s %s", step + 1, action, action_input)

        if action == "final_answer":
            state["finished"] = True
            state["final_answer"] = str(decision.get("final_answer") or "")
            new_flags = extract_flags(state["final_answer"] or "")
            state["flag_candidates"] = self._merge_flags(state.get("flag_candidates", []), new_flags)

        save_checkpoint(state["checkpoint_file"], state)
        return state

    def _act_node(self, state: AgentState) -> AgentState:
        """工具执行节点：执行上一轮 LLM 选择的工具，并写入观察。"""
        history = list(state.get("history", []))
        if not history:
            state["finished"] = True
            state["error"] = "无历史动作可执行。"
            save_checkpoint(state["checkpoint_file"], state)
            return state

        last = history[-1]
        action = str(last.get("action", ""))
        action_input = last.get("action_input", {}) or {}
        tool = self.tools.get(action)

        if tool is None:
            result = ToolResult(
                ok=False,
                output="",
                error=f"未知工具: {action}。可用工具: {', '.join(self.tools)}",
            )
        else:
            try:
                result = tool.run(**action_input)
            except ValidationError as exc:
                result = ToolResult(ok=False, output="", error=f"参数校验失败: {exc}")
            except Exception as exc:  # noqa: BLE001 - 工具异常不能让 Agent 崩溃
                LOGGER.exception("工具执行异常: %s", action)
                result = ToolResult(ok=False, output="", error=f"工具执行异常: {exc}")

        observation = result.to_observation()
        last["observation"] = observation
        history[-1] = last
        state["history"] = history

        new_flags = extract_flags(observation)
        state["flag_candidates"] = self._merge_flags(state.get("flag_candidates", []), new_flags)

        LOGGER.info("[Step %s] Observation OK=%s", last.get("step"), result.ok)
        if result.error:
            LOGGER.warning("[Step %s] Tool error: %s", last.get("step"), result.error)
        LOGGER.debug("[Step %s] Observation: %s", last.get("step"), observation)

        if int(state.get("step", 0)) >= int(state.get("max_steps", self.config.agent.max_steps)):
            state["finished"] = True
            state["final_answer"] = state.get("final_answer") or "达到最大步数限制，自动停止。"

        save_checkpoint(state["checkpoint_file"], state)
        return state

    def _route_after_think(self, state: AgentState) -> str:
        """思考后决定是否进入工具节点。"""
        if state.get("finished"):
            return "end"
        history = state.get("history", [])
        if not history:
            return "end"
        action = history[-1].get("action")
        if action == "final_answer":
            return "end"
        return "act"

    def _route_after_act(self, state: AgentState) -> str:
        """行动后决定是否继续思考。"""
        if state.get("finished"):
            return "end"
        return "think"

    @staticmethod
    def _parse_llm_json(text: str) -> Dict[str, Any]:
        """从 LLM 输出中提取 JSON。

        一些模型会误加 Markdown 代码块，这里做容错提取。
        """
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise ValueError("未找到 JSON 对象。") from None
            data = json.loads(match.group(0))

        if not isinstance(data, dict):
            raise ValueError("LLM 输出不是 JSON 对象。")
        return data

    @staticmethod
    def _merge_flags(old_flags: Any, new_flags: Any) -> list[str]:
        """合并去重 Flag 候选。"""
        merged = []
        for flag in list(old_flags or []) + list(new_flags or []):
            if flag not in merged:
                merged.append(flag)
        return merged
