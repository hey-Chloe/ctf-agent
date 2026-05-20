"""Flag 提交工具。"""

from __future__ import annotations

from typing import Any

import requests
from pydantic import BaseModel, Field

from ctf_tool.base import CtfBaseTool, ToolResult


class FlagSubmitArgs(BaseModel):
    flag: str = Field(..., description="需要提交的 flag")
    challenge_id: str | None = Field(default=None, description="CTFd challenge_id；模拟模式可不填")


class FlagSubmitTool(CtfBaseTool):
    """模拟或对接 CTFd API 提交 Flag。"""

    name = "submit_flag"
    description = "提交 Flag。默认模拟提交；若 config 中启用 ctfd，则调用 CTFd API。"
    args_schema = FlagSubmitArgs

    def __init__(self, ctfd_config: Any):
        self.ctfd_config = ctfd_config

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        if not self.ctfd_config.enabled:
            return ToolResult(
                ok=True,
                output=f"模拟提交成功: {args.flag}",
                metadata={"mode": "simulate", "challenge_id": args.challenge_id},
            )

        if not self.ctfd_config.api_url or not self.ctfd_config.api_token:
            return ToolResult(ok=False, error="CTFd 已启用，但 api_url 或 api_token 未配置。")
        if not args.challenge_id:
            return ToolResult(ok=False, error="CTFd 提交需要 challenge_id。")

        url = self.ctfd_config.api_url.rstrip("/") + "/api/v1/challenges/attempt"
        headers = {
            "Authorization": f"Token {self.ctfd_config.api_token}",
            "Content-Type": "application/json",
        }
        payload = {"challenge_id": args.challenge_id, "submission": args.flag}
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=20,
                verify=self.ctfd_config.validate_ssl,
            )
            text = resp.text
            ok = 200 <= resp.status_code < 300
            return ToolResult(ok=ok, output=text, error=None if ok else f"HTTP {resp.status_code}")
        except requests.RequestException as exc:
            return ToolResult(ok=False, error=f"CTFd 请求失败: {exc}")
