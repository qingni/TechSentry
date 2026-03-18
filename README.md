# TechSentry

TechSentry 是一个面向开发者的信息采集与智能整理工具：自动追踪 **GitHub 仓库动态**、**Hacker News 热点** 和 **GitHub Trending**，将原始信息沉淀为 Markdown 报告，并进一步用 LLM 生成更易阅读的中文总结。

它适合用来做这些事情：

- 持续关注你订阅的开源项目更新
- 快速获取当天值得看的技术热点
- 将分散的信息源整理成团队可复用的日报 / 简报
- 通过邮件或企业微信机器人把结果主动推送出去

当前项目提供 4 种使用方式：

- 后台守护进程
- Gradio Web 界面
- 交互式命令行工具
- Docker 构建与运行脚本

## 功能亮点

- **GitHub 仓库动态订阅**
  - 根据 `subscriptions.json` 中的仓库列表抓取 Issue / PR 更新
  - 导出原始 Markdown 进展文件
  - 基于 LLM 生成中文日报或简报

- **Hacker News 热点采集与汇总**
  - 采集最新热门内容
  - 输出小时级原始数据
  - 汇总生成日报总结

- **GitHub Trending 日报**
  - 抓取 GitHub Trending 日榜
  - 输出原始趋势数据
  - 自动生成中文总结报告

- **多种运行入口**
  - 守护进程适合长期运行
  - Web 界面适合手动触发与演示
  - CLI 适合开发和脚本化操作

- **通知与运行指标**
  - 支持邮件通知
  - 支持企业微信机器人通知
  - 支持 API 统计、任务 KPI、数据源健康度落盘

## 适用场景

- **个人技术情报面板**：每天自动关注重点仓库和技术热点
- **团队研发日报**：把零散更新整理成统一输出
- **开源项目观察**：长期跟踪某些仓库的迭代节奏
- **LLM 报告生成实验**：把抓取、整理、总结串成完整链路

## 工作流概览

```text
GitHub / Hacker News / GitHub Trending
                ↓
           原始 Markdown 数据
                ↓
            LLM 生成总结报告
                ↓
      本地落盘 / 邮件 / 企业微信通知
```

## 当前实现状态

为了避免 README 和代码行为脱节，这里直接按照**当前实现**说明：

- 启动 `src/daemon_process.py` 后，会**立即执行一轮**：
  - GitHub 仓库报告生成
  - Hacker News 小时报生成
  - Hacker News 日报生成
  - GitHub Trending 日报生成
- 进程常驻后，目前稳定保留的定时任务主要是：
  - 每天 `00:00` 清理历史报告目录
  - 每天 `00:05` 将 API 调用统计落盘到 `logs/api_stats.log`
  - 每天 `00:06` 将任务 KPI 与数据源健康度落盘到 `logs/job_kpi.log`、`logs/source_health.log`
- GitHub / Hacker News / GitHub Trending 的持续周期任务代码已经预留，但在当前版本中**尚未注册为长期调度任务**。

如果你的使用方式是“启动后先跑一轮采集和生成”，那么本 README 与当前代码行为是一致的。

## 环境要求

- Python `3.11+`
- 可访问外网（GitHub / Hacker News）
- 如需生成摘要报告，需要可用的 LLM 服务：
  - OpenAI 兼容接口
  - 或 Ollama 本地服务

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd TechSentry
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：

- `requests`
- `openai`
- `python-dotenv`
- `gradio`
- `loguru`
- `markdown2`
- `bs4`
- `apscheduler`

### 3. 准备环境变量

复制模板文件：

```bash
cp .env.example .env
```

最少需要配置：

```bash
GITHUB_TOKEN=your-github-token
```

如果你使用 OpenAI 兼容接口生成摘要，建议同时配置：

```bash
LLM_API_TOKEN=your-llm-api-token
LLM_BASE_URL=http://your-openai-compatible-endpoint
```

### 4. 启动守护进程

```bash
python src/daemon_process.py
```

启动后会完成初始化，并立即执行一轮采集与报告生成任务。

## 配置说明

项目配置由两部分组成：

- 根目录的 `config.json`
- 根目录的 `.env`

### `config.json`

默认内容如下：

```json
{
  "subscriptions_file": "subscriptions.json",
  "update_frequency_days": 1,
  "update_execution_time": "17:00",
  "llm": {
    "model_type": "openai",
    "openai_model_name": "gpt-5-mini",
    "ollama_model_name": "gpt-oss:20b",
    "ollama_api_url": "http://localhost:11434/v1"
  },
  "report_types": [
    "github",
    "hack_news_hours",
    "hack_news_daily",
    "github_trend_daily"
  ]
}
```

字段说明：

- `subscriptions_file`：订阅仓库列表文件路径
- `update_frequency_days`：GitHub 更新周期天数
- `update_execution_time`：预留的 GitHub 执行时间，格式为 `HH:MM`
- `llm.model_type`：`openai` 或 `ollama`
- `llm.openai_model_name`：OpenAI 模型名
- `llm.ollama_model_name`：Ollama 模型名
- `llm.ollama_api_url`：Ollama API 地址
- `report_types`：启动时预加载的提示词类型，需与 `prompts/` 中的模板对应

### `.env`

可以参考 [`.env.example`](/data/workspace/AIAgent/TechSentry/.env.example)。

#### 必填项

```bash
GITHUB_TOKEN=your-github-token
```

#### 使用 OpenAI 兼容接口时建议设置

```bash
LLM_API_TOKEN=your-llm-api-token
LLM_BASE_URL=http://your-openai-compatible-endpoint
```

说明：

- 当前 `LLM` 实现里，`model_type=openai` 实际使用的是 `LLM_API_TOKEN` 和 `LLM_BASE_URL`
- `OPENAI_API_KEY` 虽然保留在示例文件中，但当前主流程并不直接依赖它初始化客户端

#### 使用邮件通知时需要设置

```bash
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
GMAIL_SPECIAL_PASSWORD=your-gmail-app-password
```

#### 使用企业微信机器人通知时需要设置

```bash
WX_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-webhook-key
```

#### 使用 Ollama 时

当 `config.json` 中设置：

```json
{
  "llm": {
    "model_type": "ollama"
  }
}
```

代码会：

- 在本地运行时使用 `config.json` 中配置的 `ollama_api_url`
- 在容器内运行时自动切换到 `http://host.docker.internal:11434/v1`

## 运行方式

### 1. 守护进程

```bash
python src/daemon_process.py
```

适合长期运行。启动后会：

- 初始化配置、订阅、通知器与 LLM
- 立即执行一轮 GitHub / Hacker News / GitHub Trending 任务
- 启动 APScheduler 并保持进程常驻
- 每天定时写入运行统计日志

### 2. 后台脚本管理

项目提供了 [daemon.sh](/data/workspace/AIAgent/TechSentry/daemon.sh) 用于后台启动和查看状态：

```bash
chmod +x daemon.sh
./daemon.sh start
./daemon.sh status
./daemon.sh logs
./daemon.sh stop
```

支持命令：

```bash
./daemon.sh start
./daemon.sh stop
./daemon.sh restart
./daemon.sh status
./daemon.sh logs
./daemon.sh help
```

注意：

- 脚本默认优先使用 `./venv/bin/python3`
- 如果没有 `./venv`，会退回到系统 `python3`
- 如果你实际使用的是 `.venv`，建议直接手动执行 `python src/daemon_process.py`，或自行调整脚本中的 `VENV_DIR`

### 3. Web 界面

```bash
python src/gradio_server.py
```

默认监听：

- `0.0.0.0:7860`

浏览器访问：

- `http://localhost:7860`

当前界面包含 3 个标签页：

- **GitHub 项目进展**
  - 选择订阅仓库
  - 选择时间范围
  - 生成项目报告
  - 添加 / 删除订阅仓库
- **Hacker News 热点**
  - 生成当日 Hacker News 报告
- **GitHub Trend**
  - 生成 GitHub Trending 日报

说明：

- 页面中提供了模型类型和模型名称选择项
- 但当前实现里，这些选项**不会真正覆盖后端生成逻辑**
- 实际使用的模型仍以 `config.json` 为准

### 4. 交互式 CLI

```bash
python src/command_tool.py
```

启动后会进入：

```bash
Tech Sentry>
```

支持的核心命令如下。

#### 添加订阅

```text
add --repo=langchain-ai/langchain
```

#### 删除订阅

```text
remove --repo=langchain-ai/langchain
```

#### 查看订阅列表

```text
list
```

#### 拉取全部订阅更新

```text
fetch
```

#### 导出指定仓库进展

```text
export --repo=langchain-ai/langchain --relative=7d
```

也支持：

```text
export --repo=langchain-ai/langchain --since=2026-03-10 --until=2026-03-18
```

说明：

- `relative` 的优先级高于 `since/until`
- 当前 `export` 会抓取 GitHub 更新并导出原始 Markdown 进展文件
- 输出目录为 `daily_progress/<owner>/<repo>/`

#### 基于指定文件生成报告

```text
generate --file=./daily_report.md
```

说明：

- 当前实现会把 `--file` 直接传给 `ReportGenerator.generate_github_daily_report()`
- 因此 `--file` 实际表示的是**已有的原始 Markdown 输入文件路径**，不是目标输出路径

#### 其他命令

```text
help
exit
quit
```

## Docker 使用

### 构建镜像

项目提供了 [build-docker.sh](/data/workspace/AIAgent/TechSentry/build-docker.sh)：

```bash
chmod +x build-docker.sh
./build-docker.sh
```

脚本会：

- 检查 Docker 是否可用
- 读取当前 Git 分支名
- 构建镜像 `github_argus:<branch>`

也可以直接执行：

```bash
docker build -t github_argus:local .
```

### 运行镜像

项目提供了 [run-docker.sh](/data/workspace/AIAgent/TechSentry/run-docker.sh)：

```bash
chmod +x run-docker.sh
./run-docker.sh
```

或指定镜像标签：

```bash
./run-docker.sh v0.7
```

脚本会：

- 默认运行镜像 `github_argus:<tag>`
- 自动注入 `GITHUB_TOKEN`
- 可选注入 `GMAIL_SPECIAL_PASSWORD` 与 `OPENAI_API_KEY`
- 添加 `host.docker.internal:host-gateway`，方便容器访问宿主机上的 Ollama

### 默认入口

[Dockerfile](/data/workspace/AIAgent/TechSentry/Dockerfile) 中当前默认入口为：

```dockerfile
CMD ["python", "src/daemon_process.py"]
```

也就是说，容器启动后会直接运行守护进程主程序。

## 输出目录

### GitHub 仓库进展

原始进展文件输出到：

```text
daily_progress/<owner>/<repo>/<since>_<until>.md
```

例如：

```text
daily_progress/langchain-ai/langchain/2026-03-11_2026-03-18.md
```

LLM 生成后的总结文件会输出为同目录下的：

```text
*_report.md
```

### Hacker News

小时级原始数据输出到：

```text
hacker_news/<YYYY-MM-DD>/<HH>.md
```

小时报告通常为：

```text
hacker_news/<YYYY-MM-DD>/<HH>_report.md
```

日报汇总原始文件输出到：

```text
hacker_news/tech_trend/<YYYY-MM-DD>.md
```

对应日报总结文件为：

```text
hacker_news/tech_trend/<YYYY-MM-DD>_report.md
```

### GitHub Trending

原始趋势文件输出到：

```text
github_trend/<YYYY-MM-DD>.md
```

总结文件输出到：

```text
github_trend/<YYYY-MM-DD>_report.md
```

### 日志目录

```text
logs/
```

重点文件：

- `logs/app.log`：应用运行日志
- `logs/llm.log`：LLM 调用日志
- `logs/api_stats.log`：API 调用统计
- `logs/job_kpi.log`：任务 KPI
- `logs/source_health.log`：数据源健康度
- `logs/DaemonProcess.log`：通过 `daemon.sh` 启动时的输出日志
- `logs/DaemonProcess.pid`：通过 `daemon.sh` 启动时的 PID 文件

## 运行指标

守护进程当前会落盘以下运行指标：

- **任务成功率**：`success_runs / total_runs`
- **任务准点率**：按计划触发时间偏差统计
- **任务耗时 P95**
- **采集成功率**
- **报告生成成功率**
- **通知发送成功率**
- **数据新鲜度**

这些统计会在每天 `00:05` / `00:06` 由定时任务写入日志文件。

## 项目结构

```text
TechSentry/
├── config.json
├── daemon.sh
├── build-docker.sh
├── run-docker.sh
├── requirements.txt
├── subscriptions.json
├── prompts/
├── logs/
├── daily_progress/
├── github_trend/
├── hacker_news/
├── src/
│   ├── cleanup_reports.py
│   ├── command_tool.py
│   ├── config.py
│   ├── daemon_process.py
│   ├── github_api.py
│   ├── github_trend_api.py
│   ├── gradio_server.py
│   ├── hackernews_api.py
│   ├── llm.py
│   ├── logger.py
│   ├── notifier.py
│   ├── report_generator.py
│   ├── subscription.py
│   ├── utils.py
│   └── command/
└── tests/
```

## 已知限制

基于当前实现，建议你在开源说明中保留这些事实：

- **守护进程目前不是完整的持续业务调度版**
  - GitHub / Hacker News / GitHub Trending 相关业务任务目前是在启动时执行一次
  - 对应的 APScheduler 周期任务注册代码仍为注释状态

- **Gradio 模型选择当前只是界面层配置**
  - 不会覆盖 `config.json` 中的模型设置

- **CLI 的 `generate --file` 参数语义容易误解**
  - 当前实现接收的是输入 Markdown 文件路径，而不是输出路径

- **通知发送没有做细粒度开关**
  - 进入通知逻辑后，会尝试同时发送邮件和企业微信机器人消息
  - 如果相关配置为空，可能导致发送失败或请求异常

- **`daemon.sh` 默认使用 `./venv`**
  - 如果你的实际环境是 `.venv`，需要自行调整脚本或直接手动启动

## License

本项目采用 [MIT License](LICENSE)。
