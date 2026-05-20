# CTF-Agent

CTF-Agent 是一个基于 ReAct 思路、LangGraph 状态机和 LangChain LLM 接口的自动化 CTF 解题 Agent 示例项目。它会读取题目描述、URL 或附件路径，让 LLM 在多轮循环中选择工具、观察结果、继续推理，最终输出 Flag 候选或最终答案。

> 仅用于你拥有授权的 CTF 比赛、靶场、教学环境或本地实验环境。请勿用于未授权目标。

## 功能概览

- ReAct 循环：思考 → 行动 → 观察 → 再思考。
- LangGraph 状态机：`think` 节点负责 LLM 决策，`act` 节点负责工具调用。
- 多 LLM 后端：OpenAI API、DeepSeek OpenAI-compatible API、Ollama 本地模型。
- Docker 隔离执行：默认所有命令都在名为 `ctf-target` 的容器中运行。
- 工具系统：统一 `CtfBaseTool` 接口，内置命令执行、Python 执行、nmap、dirsearch、sqlmap、binwalk、strings、图片隐写初查、Flag 提交。
- 存档恢复：每轮状态写入 `checkpoints/`，支持 `--resume` 继续运行。
- 日志调试：控制台和 `logs/` 同时记录思考、动作、观察和错误。

## 项目结构

```text
.
├── agent/                  # Agent 核心循环和提示词
├── ctf_tool/               # 所有工具类
├── utils/                  # 配置、LLM、Docker/SSH、日志、checkpoint
├── cli/                    # 命令行入口
├── logs/                   # 日志目录
├── checkpoints/            # Agent 存档目录
├── attachments/            # 题目附件目录
├── config.json             # 默认 Ollama 本地配置，无密钥
├── config_template.json    # 配置模板
├── config_openai_example.json
├── config_ollama_example.json
├── config_deepseek_example.json
├── requirements.txt
├── Dockerfile
└── README.md
```

## 1. 安装 Python 依赖

建议 Python 3.10+，示例使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. 构建并启动工具容器

构建镜像：

```bash
docker build -t ctf-agent-env .
```

启动容器，容器名必须与配置中的 `ctf-target` 一致：

```bash
docker run -d --name ctf-target \
  --cap-add=NET_ADMIN \
  -v "$PWD:/work" \
  ctf-agent-env
```

如果你需要让容器访问本地靶场服务，可按实际情况改为 `--network host`（Linux 可用）或使用 Docker Compose 自建网络。

## 3. 配置 LLM

项目自带 `config.json`，默认使用本地 Ollama：

```json
{
  "llm": {
    "provider": "ollama",
    "model": "llama3.1",
    "api_base": "http://localhost:11434"
  }
}
```

启动 Ollama 并拉取模型：

```bash
ollama pull llama3.1
ollama serve
```

OpenAI 配置示例见 `config_openai_example.json`，复制为 `config.json` 并填入自己的密钥：

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "api_key": "YOUR_OPENAI_API_KEY",
    "api_base": "https://api.openai.com/v1"
  }
}
```

DeepSeek 配置示例见 `config_deepseek_example.json`：

```json
{
  "llm": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "api_key": "YOUR_DEEPSEEK_API_KEY",
    "api_base": "https://api.deepseek.com"
  }
}
```

不要把真实 API Key 提交到 Git。

## 4. 运行示例

Web 题目：

```bash
python cli/main.py --url http://example.com --question "这是一个授权 CTF Web 题，请尝试找到 flag。"
```

附件题目：

```bash
cp /path/to/challenge.png attachments/
python cli/main.py --file attachments/challenge.png --question "图片隐写题，找出 flag。"
```

从题目文件读取：

```bash
python cli/main.py --question-file question.txt --url http://challenge.local
```

启用 DEBUG 日志：

```bash
python cli/main.py --url http://example.com --debug
```

限制最大步数：

```bash
python cli/main.py --url http://example.com --max-steps 10
```

从 checkpoint 恢复：

```bash
python cli/main.py --resume checkpoints/run_20250101_120000.json
```

## 5. 工具说明

所有工具都继承 `ctf_tool.base.CtfBaseTool`，具有统一字段：

- `name`：工具名，LLM 调用时使用。
- `description`：工具自然语言描述。
- `args_schema`：Pydantic 参数 schema。
- `run(**kwargs)`：执行逻辑，返回 `ToolResult`。

内置工具：

| 工具名 | 说明 |
|---|---|
| `run_command` | 在 Docker 容器内执行 shell 命令 |
| `run_python` | 在 Docker 容器内执行 Python 代码 |
| `nmap_scan` | nmap 端口和服务扫描 |
| `dirsearch_scan` | Web 目录爆破 |
| `sqlmap_check` | SQL 注入检测 |
| `file_inspect` | 文件类型、大小、哈希识别 |
| `binwalk_analyze` | binwalk 分析和提取 |
| `strings_search` | strings 查找可见字符串 |
| `image_stego_check` | exiftool、zsteg、steghide 图片隐写初查 |
| `submit_flag` | 模拟或 CTFd API 提交 Flag |

添加新工具时，在 `ctf_tool/` 中新增类，并在 `ctf_tool/registry.py` 注册即可。

## 6. CTFd 提交配置

默认是模拟提交：

```json
"ctfd": {
  "enabled": false,
  "api_url": "",
  "api_token": "",
  "validate_ssl": true
}
```

如需接入 CTFd：

```json
"ctfd": {
  "enabled": true,
  "api_url": "https://ctfd.example.com",
  "api_token": "YOUR_CTFD_TOKEN",
  "validate_ssl": true
}
```

LLM 调用 `submit_flag` 时需要提供 `challenge_id`。

## 7. 常见问题

### Docker 环境检查失败

确认容器存在且正在运行：

```bash
docker ps
docker start ctf-target
```

### 容器内找不到附件

默认启动命令会把当前项目目录挂载到容器 `/work`。请把附件放到 `attachments/`，并使用相对路径：

```bash
python cli/main.py --file attachments/a.zip --question "分析附件"
```

### dirsearch / zsteg 构建失败

不同系统源可能有差异。可以进入容器手工安装：

```bash
docker exec -it ctf-target bash
pip install dirsearch
gem install zsteg
```

### LLM 输出不是 JSON

换一个指令遵循能力更强的模型，或在 `agent/prompts.py` 中收紧提示词。当前代码会尝试从 Markdown 代码块中容错提取 JSON。

## 8. 安全边界

本项目默认把命令限制在 `ctf-target` 容器中执行，但工具本身仍具备网络探测和漏洞检测能力。请务必只在授权范围内使用，并根据比赛规则控制扫描频率和强度。
