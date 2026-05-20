"""CTF-Agent 命令行入口。

示例：
    python cli/main.py --url http://example.com
    python cli/main.py --file attachments/challenge.png --question "找出图片中的 flag"
    python cli/main.py --resume checkpoints/run_20250101_120000.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# 允许用户直接执行 python cli/main.py，而无需安装为包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent import CtfReactAgent  # noqa: E402
from ctf_tool import build_default_tools  # noqa: E402
from utils.config import load_config  # noqa: E402
from utils.executor_factory import build_executor  # noqa: E402
from utils.logger import setup_logging  # noqa: E402

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="CTF-Agent: LLM 驱动的 ReAct 自动化 CTF 解题 Agent")
    parser.add_argument("--url", help="Web 题目地址，例如 http://example.com")
    parser.add_argument("--file", help="附件文件路径，建议放在 attachments/ 下")
    parser.add_argument("--question", help="题目文本描述")
    parser.add_argument("--question-file", help="从文件读取题目描述，例如 question.txt")
    parser.add_argument("--config", default="config.json", help="配置文件路径，默认 config.json")
    parser.add_argument("--resume", help="从 checkpoints/*.json 恢复")
    parser.add_argument("--max-steps", type=int, help="覆盖配置中的最大步数")
    parser.add_argument("--debug", action="store_true", help="启用 DEBUG 日志")
    return parser.parse_args()


def build_challenge(args: argparse.Namespace) -> Dict[str, Any]:
    """整合题目输入。"""
    description_parts: list[str] = []
    if args.question:
        description_parts.append(args.question)
    if args.question_file:
        description_parts.append(Path(args.question_file).read_text(encoding="utf-8"))

    if not args.url and not args.file and not description_parts:
        print("请输入题目描述，结束后按 Ctrl-D / Ctrl-Z：")
        description_parts.append(sys.stdin.read().strip())

    file_path = normalize_file_path(args.file) if args.file else None
    return {
        "description": "\n".join(part for part in description_parts if part).strip(),
        "url": args.url,
        "file": file_path,
        "notes": "所有相对路径默认映射到容器 /work 下；建议将附件放入 attachments/。",
    }


def normalize_file_path(path: str) -> str:
    """把本机相对路径转换为容器内 /work 路径提示。"""
    p = Path(path)
    if str(path).startswith("/work/"):
        return str(path)
    if not p.is_absolute():
        return "/work/" + str(p).replace("\\", "/")
    try:
        rel = p.resolve().relative_to(PROJECT_ROOT.resolve())
        return "/work/" + str(rel).replace("\\", "/")
    except ValueError:
        # 绝对路径不在项目目录下时，容器默认访问不到，仍保留原值并在提示中提醒。
        return str(p)


def main() -> int:
    """CLI 主函数。"""
    args = parse_args()
    config = load_config(args.config)
    if args.debug:
        config.agent.debug = True
    log_file = setup_logging(config.agent.log_dir, debug=config.agent.debug)
    LOGGER.info("日志文件: %s", log_file)

    executor = build_executor(config)
    health_error = None
    try:
        executor.healthcheck()
    except Exception as exc:  # noqa: BLE001
        health_error = str(exc)
        LOGGER.warning("执行环境检查失败，Agent 仍会启动，但工具调用可能失败: %s", exc)

    tools = build_default_tools(config, executor)
    agent = CtfReactAgent(config, tools)

    challenge = None if args.resume else build_challenge(args)
    if challenge and health_error:
        challenge["environment_warning"] = health_error

    final_state = agent.run(
        challenge=challenge,
        resume_checkpoint=args.resume,
        max_steps=args.max_steps,
    )

    print("\n========== CTF-Agent 运行结束 ==========")
    print("Checkpoint:", final_state.get("checkpoint_file"))
    print("Flag 候选:", final_state.get("flag_candidates"))
    print("最终答案:", final_state.get("final_answer"))
    if final_state.get("error"):
        print("错误:", final_state.get("error"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
