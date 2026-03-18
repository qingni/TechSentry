import gradio as gr
from subscription import SubscriptionManager
from config import Config
from llm import LLM
from github_api import GitHubAPI
from report_generator import ReportGenerator
from utils import Utils
from hackernews_api import HackerNewsAPI
from github_trend_api import GithubTrendAPI

config = Config()
github_api = GitHubAPI(config.github_token)
llm = LLM(config)
report_generator = ReportGenerator(llm, config.report_types)
subscription_manager = SubscriptionManager(config.subscriptions_file)
hack_news_api = HackerNewsAPI()
github_trend_api = GithubTrendAPI()
  
def generate_github_report(repo, relative):
    relative_time = Utils.get_key_by_description(relative)
    updates = github_api.fetch_updates(repo, relative=relative_time)
    markdown = github_api.export_daily_progress(repo, updates, relative=relative_time)
    report, report_file_path = report_generator.generate_github_daily_report(markdown)
    
    return report, report_file_path

def generate_hacker_news_report():
  markdown_file_path = hack_news_api.generate_daily_report()
  if markdown_file_path is None:
    return "❌ 生成Hacker News报告失败：当日数据目录不存在或没有有效的小时报告文件，请先运行数据采集任务。", None
  report, report_file_path = report_generator.generate_hack_news_daily_report(markdown_file_path)
  return report, report_file_path

def generate_github_trend_report():
  repos = github_trend_api.get_github_trending()
  if not repos:
    return "❌ 生成GitHub Trend报告失败：无法获取GitHub趋势数据，请检查网络连接。", None
  markdown_file_path = github_trend_api.generate_daily_github_trend(repos)
  if markdown_file_path is None:
    return "❌ 生成GitHub Trend报告失败：无法生成趋势数据文件。", None
  report, report_file_path = report_generator.generate_github_trend_daily_report(markdown_file_path)
  return report, report_file_path

# 定义一个回调函数，用于根据 Radio 组件的选择返回不同的 Dropdown 选项
def update_model_list(model_type):
    model_choices = default_model_list(model_type)

    return gr.Dropdown(
            choices=model_choices, 
            label="选择模型", 
            info="默认OpenAI相关模型",
            value=model_choices[0] if model_choices else None,  # 设置默认值
            interactive=True  # 明确设置可交互
    )

def default_model_list(model_type):
  model_choices = ["gpt-5-mini", "gpt-5"]
  if model_type == "ollama":
      model_choices = ["gpt-oss:20b", "deepseek-r1:8b", "qwen3:8b"]
  return model_choices

def add_github_subscription(repo, current_subscriptions):
  """添加GitHub仓库到订阅列表"""
    # 简单验证输入格式
  if repo and "/" in repo:
    # 确保没有重复添加
    if repo not in current_subscriptions:
      # 添加新仓库到列表
      repo = repo.replace(" ", "")
      subscription_manager.add_subscription(repo)
      
    available_repos = gr.Dropdown(
      subscription_manager.get_subscriptions(), 
      label="已订阅GitHub项目",
      value=repo # 新添加的repo设置为默认值
    )
    return available_repos, "", available_repos
  else:
    # 格式不正确，返回原始列表和错误提示
    return current_subscriptions, "格式错误！请使用 owner/repo 格式"

def remove_github_subscription(repo):
  """添加GitHub仓库到订阅列表"""
  subscription_manager.remove_subscription(repo)
  subscription_list = subscription_manager.get_subscriptions()
  available_repos = gr.Dropdown(
    subscription_list, 
    label="已订阅GitHub项目",
    value=subscription_list[0]
  )
  return available_repos, available_repos
  
# 创建模型选择UI的公共函数
def create_model_selection():
    """
    创建模型选择UI组件
    返回: (model_type_radio, model_name_dropdown)
    """
    model_type = gr.Radio(
        ["ollama", "openai"], 
        label="模型类型", 
        value="ollama",
        info="使用 Ollama 私有化模型服务 或 OpenAI GPT API"
    )
    
    model_choices = default_model_list('ollama')
    model_name = gr.Dropdown(
        choices=model_choices, 
        label="选择模型", 
        info="默认OpenAI相关模型",
        value=model_choices[0],
        interactive=True
    )
    
    model_type.change(fn=update_model_list, inputs=model_type, outputs=model_name)
    return model_type, model_name

# 创建报告生成区域的公共函数
def create_report_section(generate_func, inputs=[]):
    """
    创建报告生成区域
    generate_func: 生成报告的函数
    inputs: 生成报告所需的输入组件列表
    """
    button = gr.Button("生成报告")
    markdown_output = gr.Markdown()
    file_output = gr.File(label="下载报告")
    
    button.click(
        fn=generate_func, 
        inputs=inputs, 
        outputs=[markdown_output, file_output]
    )
    
    return button, markdown_output, file_output
      
with gr.Blocks(title="TechSentry", css="""
    /* 按钮公共样式 - 提取重复属性 */
    .custom-button {
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        transition: background-color 0.3s ease !important;
        cursor: pointer !important;
    }
    
    /* 添加按钮样式 */
    .add-button {
        background-color: #4CAF50 !important; /* 绿色 */
        color: white !important;
    }
    
    /* 删除按钮样式 */
    .delete-button {
        background-color: #f44336 !important; /* 红色 */
        color: white !important;
    }
    
    /* 悬停效果 */
    .add-button:hover {
        background-color: #45a049 !important; /* 深一点的绿色 */
    }
    
    .delete-button:hover {
        background-color: #d32f2f !important; /* 深一点的红色 */
    }
    
    /* 激活效果（点击时） */
    .add-button:active {
        background-color: #3d8b40 !important;
    }
    
    .delete-button:active {
        background-color: #b71c1c !important;
    }
    
    /* 文本框样式优化 */
    .gr-textbox {
        border-radius: 4px !important;
    }
    
    /* 下拉框样式优化 */
    .gr-dropdown {
        border-radius: 4px !important;
    }
""") as demo:
  # GitHub项目进展Tab
  with gr.Tab("GitHub 项目进展"):
    gr.Markdown("## GitHub 项目进展")
    
    # 使用公共函数创建模型选择UI
    model_type, model_name = create_model_selection()
    
    # 创建订阅列表和时间周期选择
    subscription_list = gr.Dropdown(
        subscription_manager.get_subscriptions(), 
        label="已订阅GitHub项目",
    )
                
    relative = gr.Dropdown(
        Utils.get_all_relative_time_descriptions(), 
        label="时间周期", 
        info="生成GitHub项目过去一段时间的进展"
    )
    
    # 使用公共函数创建报告区域
    _, markdown_output, file_output = create_report_section(
        generate_github_report,
        inputs=[subscription_list, relative]
    )
    
    with gr.Accordion("管理GitHub订阅仓库", open=False):
        gr.Markdown("在这里添加或删除你想要订阅的GitHub仓库")
        
        with gr.Row():
            with gr.Column(scale=1):
                repo_input = gr.Textbox(
                    label="输入要订阅的仓库", 
                    placeholder="格式：owner/repo",
                    elem_classes=["repo-input"]
                )
                add_btn = gr.Button("添加仓库", elem_classes=["custom-button", "add-button"])
            
            with gr.Column(scale=1):
                delete_list = gr.Dropdown(
                    subscription_manager.get_subscriptions(), 
                    label="已订阅的GitHub项目",
                    interactive=True
                )
                delete_btn = gr.Button("删除仓库", elem_classes=["custom-button", "delete-button"])
                
            add_btn.click(fn=add_github_subscription, inputs=[repo_input, subscription_list], outputs=[subscription_list, repo_input, delete_list])
            delete_btn.click(fn=remove_github_subscription, inputs=[delete_list], outputs=[delete_list, subscription_list])
  # Hacker News热点Tab
  with gr.Tab("Hacker News热点"):
    gr.Markdown("## Hacker News热点")
    
    # 使用公共函数创建模型选择UI
    model_type, model_name = create_model_selection()
    
    # 使用公共函数创建报告区域
    _, markdown_output, file_output = create_report_section(
        generate_hacker_news_report
    )
  
  # GitHub Trend每日趋势Tab
  with gr.Tab("GitHub Trend"):
    gr.Markdown("## GitHub Trend每日趋势")
    
    # 使用公共函数创建模型选择UI
    model_type, model_name = create_model_selection()
    
    # 使用公共函数创建报告区域
    _, markdown_output, file_output = create_report_section(
        generate_github_trend_report
    )
  

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False, debug=True)
