# TechSentry - 智能开发监控助手

## 目录
- [TechSentry - 智能开发监控助手](#techsentry---智能开发监控助手)
  - [目录](#目录)
    - [关键成果：](#关键成果)
    - [量化数据评判标准：](#量化数据评判标准)
  - [核心功能](#核心功能)
  - [安装指南](#安装指南)
  - [使用说明](#使用说明)
    - [守护进程管理](#守护进程管理)
    - [启动Web界面](#启动web界面)
      - [访问地址](#访问地址)
      - [可选参数](#可选参数)
      - [界面功能预览](#界面功能预览)
      - [界面截图](#界面截图)
    - [命令行工具使用](#命令行工具使用)
      - [命令行界面示例](#命令行界面示例)
      - [添加订阅](#添加订阅)
      - [移除订阅](#移除订阅)
      - [列出所有订阅](#列出所有订阅)
      - [立即获取更新](#立即获取更新)
      - [导出每日进度](#导出每日进度)
      - [生成每日报告](#生成每日报告)
      - [帮助信息](#帮助信息)
      - [退出工具](#退出工具)
  - [项目结构](#项目结构)
  - [许可证](#许可证)

TechSentry是一个自动化监控工具，用于跟踪GitHub仓库更新、HackerNews热点和GitHub趋势项目，并生成每日报告。

### 关键成果：
- 已建立**可审计、可复现**的指标链路，核心统计按日落盘，支持持续追踪与回溯
- 调度系统采用统一时区（`Asia/Shanghai`），并通过事件监听统计任务执行质量
- 三类数据源（GitHub/HackerNews/GitHub Trend）已接入统一健康度口径（采集、报告、通知）
- 关键指标从“宣传性数字”切换为“运行期实测数据”，避免口径漂移

### 量化数据评判标准：
1. **任务成功率（Success Rate）**
   - 定义：`success_runs / total_runs`
   - 采集方式：APScheduler执行事件（成功/失败）
   - 存储位置：`logs/job_kpi.log`
   - 建议目标：`>= 99.0%`
2. **任务准点率（On-time Rate）**
   - 定义：`|实际触发时间 - 计划触发时间| <= 60秒` 的执行占比
   - 采集方式：APScheduler计划时间与实际时间偏差
   - 存储位置：`logs/job_kpi.log`
   - 建议目标：`>= 98.0%`
3. **任务耗时P95（P95 Duration）**
   - 定义：单次任务执行耗时的P95分位数
   - 采集方式：任务提交/执行事件的耗时差
   - 存储位置：`logs/job_kpi.log`
   - 建议目标：按任务类型分别设定阈值并持续收敛
4. **采集成功率（Collection Success Rate）**
   - 定义：`success / attempts`
   - 采集范围：`github`、`hackernews`、`github_trend`
   - 存储位置：`logs/source_health.log`
   - 建议目标：`>= 97.0%`
5. **报告生成成功率（Report Success Rate）**
   - 定义：`report_success / (report_success + report_failure)`
   - 存储位置：`logs/source_health.log`
   - 建议目标：`>= 99.0%`
6. **通知发送成功率（Notify Success Rate）**
   - 定义：`notify_success / (notify_success + notify_failure)`
   - 存储位置：`logs/source_health.log`
   - 建议目标：`>= 99.0%`
7. **数据新鲜度（Data Freshness）**
   - 定义：当前时间与数据源最近一次成功采集时间的分钟差
   - 存储位置：`logs/source_health.log`
   - 建议目标：不超过各数据源调度周期的`1.5`倍

> 说明：上述指标以运行期真实数据为准。建议先连续运行7天形成基线，再将“建议目标”调整为“当前值+改进目标”。

## 核心功能

- **GitHub仓库监控**：定时检查订阅仓库的更新（提交、PR、Issue）
- **HackerNews热点追踪**：每小时抓取热门故事，每日生成摘要报告
- **GitHub趋势分析**：每日收集GitHub热门仓库并生成趋势报告
- **守护进程**：后台定时任务管理，支持自定义执行频率和时间
- **Web界面**：通过Gradio提供可视化操作界面
- **命令行工具**：交互式命令接口，支持手动触发任务和系统管理
- **通知系统**：支持多种通知方式（邮件、企微机器人等）
- **日志系统**：多级日志记录（DEBUG/INFO/WARNING/ERROR），支持日志轮转和持久化存储
- **自动清理**：定期清理过期报告文件

## 安装指南

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/TechSentry.git
cd TechSentry
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置设置：
在`config.json`填写您的配置：
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
  "report_types":[
    "github",
    "hack_news_hours",
    "hack_news_daily",
    "github_trend_daily"
  ]
}
```
4. 环境变量设置
为保证数据安全，需要在环境变量中设置项目需要的github token，以及调用OpenAI API Key。若需要使用gmail邮箱，还需要设置gmail邮箱专用密码。
```bash
# github token（用于拉取github订阅仓库时）
export GITHUB_TOKEN="xxx"
# OpenAI API Key
export OPENAI_API_KEY="xxx"
# gmail邮箱专用密码
export GMAIL_SPECIAL_PASSWORD="xxx"
# LLM API Token (可选，用于覆盖默认的OpenAI API Key)
export LLM_API_TOKEN="xxx"
# LLM Base URL (可选，用于自定义API地址)
export LLM_BASE_URL="xxx"
# 邮件通知配置 (可选)
export EMAIL_SMTP_SERVER="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_FROM="xxx"
export EMAIL_TO="xxx"
# 企微机器人通知配置 (可选)
export WX_WEBHOOK_URL="xxx"
```

## 使用说明

### 守护进程管理

守护进程会在后台运行定时任务，在配置的时间点自动生成报告。使用 `daemon.sh` 脚本管理后台监控进程：

```bash
# 启动守护进程
./daemon.sh start

# 停止守护进程
./daemon.sh stop

# 重启守护进程
./daemon.sh restart

# 查看守护进程状态
./daemon.sh status

# 实时查看日志输出
./daemon.sh logs

# 显示帮助信息
./daemon.sh help
```

常用操作示例：
```bash
# 启动并查看状态
./daemon.sh start && ./daemon.sh status

# 重启并跟踪日志
./daemon.sh restart && ./daemon.sh logs
```

### 启动Web界面

运行以下命令启动交互式监控面板：
```bash
python src/gradio_server.py
```

#### 访问地址
启动成功后，在浏览器中打开 [http://localhost:7860](http://localhost:7860) 即可使用界面。

#### 可选参数
| 参数       | 说明                          | 默认值 |
|------------|-------------------------------|--------|
| `--share`  | 生成公开可访问的临时链接       | False  |
| `--debug`  | 启用调试模式（显示详细错误信息）| False  |

示例：
```bash
# 生成公开链接并启用调试模式
python src/gradio_server.py --share --debug
```

#### 界面功能预览
1. **GitHub项目进展**：
   - 选择订阅仓库
   - 设置监控时间范围
   - 生成项目进展报告
   - 管理订阅仓库（添加/删除）

2. **Hacker News热点**：
   - 一键生成当日热门技术故事摘要

3. **GitHub趋势**：
   - 查看当日热门开源项目
   - 生成趋势分析报告

#### 界面截图
以下是Web界面的功能截图：

- **GitHub仓库监控界面**  
  ![GitHub仓库监控](screenshot/githubrepo.png)

- **Hacker News热点界面**  
  ![Hacker News热点](screenshot/hackernews.png)

- **GitHub趋势界面**  
  ![GitHub趋势](screenshot/githubtrend.png)


### 命令行工具使用
启动命令行工具：
```bash
python src/command_tool.py
```

#### 命令行界面示例
![命令行工具界面](screenshot/command_line.png) *（截图待添加）*

工具提供以下命令：

#### 添加订阅
```
add <repo>
  参数:
    --repo      GitHub仓库路径 (格式: owner/repo)
  示例:
    add --repo=langchain-ai/langchain
```

#### 移除订阅
```
remove <repo>
  参数:
    --repo      已订阅的仓库路径 (格式: owner/repo)
  示例:
    remove --repo=langchain-ai/langchain
```

#### 列出所有订阅
```
list
  示例:
    list
```

#### 立即获取更新
```
fetch
  示例:
    fetch
```

#### 导出每日进度
```
export <repo> [since] [until] [relative]
  参数:
    --repo        仓库路径 (格式: owner/repo，必填)
    --since       起始日期 (格式: YYYY-MM-DD，可选)
    --until       结束日期 (格式: YYYY-MM-DD，可选)
    --relative    相对时间 (例如: 24hours, 7d，可选)
  说明:
    时间参数优先级: relative > since/until，不指定则默认今天
  示例:
    export --repo=langchain-ai/langchain --since="" --until="" --relative=7d       # 过去7天
```

#### 生成每日报告
```
generate <file>
  参数:
    --file        输出文件路径 (例如: ./report.md)
  示例:
    generate --file=./daily_report.md
```

#### 帮助信息
```
help
```

#### 退出工具
```
exit 或 quit
```

## 项目结构

```
├── src/                    # 主程序源代码
│   ├── command/            # 命令行处理模块
│   ├── daemon_process.py   # 守护进程主程序
│   ├── github_api.py       # GitHub API封装
│   ├── gradio_server.py    # Web界面服务器
│   ├── hackernews_api.py   # HackerNews API封装
│   ├── llm.py              # 大语言模型集成
│   ├── logger.py           # 日志模块
│   ├── notifier.py         # 通知模块
│   ├── report_generator.py # 报告生成器
│   └── utils.py            # 工具函数
├── daily_progress/         # GitHub仓库日报
├── github_trend/           # GitHub趋势报告
├── hacker_news/            # HackerNews报告
│   └── tech_trend/         # 技术趋势子报告
├── logs/                   # 系统日志
├── prompts/                # LLM提示词模板
├── config.json             # 配置文件
├── requirements.txt        # Python依赖
└── daemon.sh               # 守护进程管理脚本
```

## 许可证

本项目采用 [MIT 许可证](LICENSE)
