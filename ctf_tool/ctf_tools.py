"""常见 CTF 工具封装。"""

from __future__ import annotations

import shlex
from typing import Any

from pydantic import BaseModel, Field

from ctf_tool.base import CtfBaseTool, ToolResult
from utils.executor import BaseExecutor


def q(value: str) -> str:
    """shell 安全引用。"""
    return shlex.quote(str(value))


class NmapArgs(BaseModel):
    target: str = Field(..., description="扫描目标，例如 127.0.0.1 或 challenge.example.com")
    ports: str | None = Field(default=None, description="端口范围，例如 80,443 或 1-1000")
    extra_args: str = Field(default="", description="额外 nmap 参数，例如 -Pn；高级用法才需要")
    timeout: int | None = Field(default=180, description="超时时间，单位秒")


class NmapTool(CtfBaseTool):
    name = "nmap_scan"
    description = "使用 nmap 进行端口和服务识别。适合网络、Web、misc 服务入口探测。"
    args_schema = NmapArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        port_part = f"-p {q(args.ports)}" if args.ports else ""
        command = f"nmap -sV -sC {port_part} {args.extra_args} {q(args.target)}"
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class DirsearchArgs(BaseModel):
    url: str = Field(..., description="目标 URL，例如 http://example.com/")
    wordlist: str = Field(default="/usr/share/wordlists/dirb/common.txt", description="字典路径")
    extensions: str = Field(default="php,txt,html,js", description="扩展名列表，逗号分隔")
    extra_args: str = Field(default="", description="额外 dirsearch 参数")
    timeout: int | None = Field(default=300, description="超时时间，单位秒")


class DirsearchTool(CtfBaseTool):
    name = "dirsearch_scan"
    description = "使用 dirsearch 对 Web 目录和文件进行初步爆破。"
    args_schema = DirsearchArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        command = (
            "if command -v dirsearch >/dev/null 2>&1; then "
            f"dirsearch -u {q(args.url)} -w {q(args.wordlist)} -e {q(args.extensions)} --random-agent {args.extra_args}; "
            "else python3 -m dirsearch "
            f"-u {q(args.url)} -w {q(args.wordlist)} -e {q(args.extensions)} --random-agent {args.extra_args}; fi"
        )
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class SqlmapArgs(BaseModel):
    url: str = Field(..., description="疑似 SQL 注入 URL")
    data: str | None = Field(default=None, description="POST 数据，例如 id=1&name=a")
    cookie: str | None = Field(default=None, description="Cookie 字符串")
    risk: int = Field(default=1, description="sqlmap risk，1-3")
    level: int = Field(default=1, description="sqlmap level，1-5")
    extra_args: str = Field(default="", description="额外 sqlmap 参数")
    timeout: int | None = Field(default=600, description="超时时间，单位秒")


class SqlmapTool(CtfBaseTool):
    name = "sqlmap_check"
    description = "使用 sqlmap 对授权 CTF Web 目标进行 SQL 注入检测。默认 batch 模式。"
    args_schema = SqlmapArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        data_part = f" --data {q(args.data)}" if args.data else ""
        cookie_part = f" --cookie {q(args.cookie)}" if args.cookie else ""
        command = (
            f"sqlmap -u {q(args.url)}{data_part}{cookie_part} "
            f"--batch --random-agent --risk {int(args.risk)} --level {int(args.level)} {args.extra_args}"
        )
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class FileTypeArgs(BaseModel):
    file_path: str = Field(..., description="容器内文件路径，例如 /work/attachments/a.zip")
    timeout: int | None = Field(default=60, description="超时时间，单位秒")


class FileTypeTool(CtfBaseTool):
    name = "file_inspect"
    description = "识别附件类型、大小和哈希。适合附件分析第一步。"
    args_schema = FileTypeArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        path = q(args.file_path)
        command = (
            f"if [ ! -e {path} ]; then echo '文件不存在: {path}' >&2; exit 2; fi; "
            f"file {path}; ls -lh {path}; sha256sum {path}"
        )
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class BinwalkArgs(BaseModel):
    file_path: str = Field(..., description="需要分析或提取的文件路径")
    extract: bool = Field(default=False, description="是否执行 binwalk -eM 提取")
    output_dir: str = Field(default="/work/attachments/_binwalk", description="提取输出目录")
    timeout: int | None = Field(default=300, description="超时时间，单位秒")


class BinwalkTool(CtfBaseTool):
    name = "binwalk_analyze"
    description = "使用 binwalk 分析或提取固件、图片、压缩包中的嵌入数据。"
    args_schema = BinwalkArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        file_path = q(args.file_path)
        if args.extract:
            command = f"mkdir -p {q(args.output_dir)} && binwalk -eM --directory {q(args.output_dir)} {file_path}"
        else:
            command = f"binwalk {file_path}"
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)


class StringsArgs(BaseModel):
    file_path: str = Field(..., description="需要查找可见字符串的文件路径")
    min_length: int = Field(default=4, description="strings -n 的最小长度")
    pattern: str | None = Field(default=None, description="可选 grep -Ei 过滤表达式，例如 flag|ctf")
    max_lines: int = Field(default=300, description="最多返回多少行")
    timeout: int | None = Field(default=120, description="超时时间，单位秒")


class StringsTool(CtfBaseTool):
    name = "strings_search"
    description = "对二进制或附件运行 strings，并可用正则过滤 flag、URL、密码等线索。"
    args_schema = StringsArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        command = f"strings -a -n {int(args.min_length)} {q(args.file_path)}"
        if args.pattern:
            command += f" | grep -Ei {q(args.pattern)}"
        command += f" | head -n {int(args.max_lines)}"
        result = self.executor.run(command, timeout=args.timeout)
        # grep 无匹配时会返回 1，但这不是致命错误。
        ok = result.exit_code in (0, 1)
        return ToolResult(ok=ok, output=result.output, error=result.error if result.exit_code not in (0, 1) else None)


class StegoArgs(BaseModel):
    file_path: str = Field(..., description="图片或可疑隐写文件路径")
    mode: str = Field(default="all", description="all、zsteg、steghide、exiftool 之一")
    passphrase: str = Field(default="", description="steghide 可选口令，不知道则留空")
    timeout: int | None = Field(default=300, description="超时时间，单位秒")


class StegoTool(CtfBaseTool):
    name = "image_stego_check"
    description = "图片隐写初步检查：file/exiftool/zsteg/steghide。适合 PNG、BMP、JPG 等附件。"
    args_schema = StegoArgs

    def __init__(self, executor: BaseExecutor):
        self.executor = executor

    def run(self, **kwargs: Any) -> ToolResult:
        args = self.args_schema(**kwargs)
        file_path = q(args.file_path)
        mode = args.mode.lower().strip()
        commands = []
        if mode in ("all", "exiftool"):
            commands.append(f"exiftool {file_path} 2>/dev/null || true")
        if mode in ("all", "zsteg"):
            commands.append(
                f"if command -v zsteg >/dev/null 2>&1; then zsteg -a {file_path}; else echo 'zsteg 未安装'; fi"
            )
        if mode in ("all", "steghide"):
            pass_part = f"-p {q(args.passphrase)}" if args.passphrase else "-p ''"
            commands.append(
                f"if command -v steghide >/dev/null 2>&1; then steghide info {file_path} {pass_part}; else echo 'steghide 未安装'; fi"
            )
        if not commands:
            return ToolResult(ok=False, error=f"未知 mode: {args.mode}")
        command = "\necho '--- next check ---'\n".join(commands)
        result = self.executor.run(command, timeout=args.timeout)
        return ToolResult(ok=result.exit_code == 0, output=result.output, error=result.error)
