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
  report, report_file_path = report_generator.generate_hack_news_daily_report(markdown_file_path)
  return report, report_file_path

def generate_github_trend_report():
  repos = github_trend_api.get_github_trending()
  markdown_file_path = github_trend_api.generate_daily_github_trend(repos)
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
  model_choices = ["gpt-4o-mini", "gpt-3.5-turbo"]
  if model_type == "ollama":
      model_choices = ["gpt-oss:20b", "deepseek-r1:8b", "qwen3:8b"]
  return model_choices

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
      
with gr.Blocks(title="GitHubArgus") as demo:
  # GitHub项目进展Tab
  with gr.Tab("GitHub 项目进展"):
    gr.Markdown("## GitHub 项目进展")
    
    # 使用公共函数创建模型选择UI
    model_type, model_name = create_model_selection()
    
    # 创建订阅列表和时间周期选择
    subscription_list = gr.Dropdown(
        subscription_manager.get_subscriptions(), 
        label="订阅列表", 
        info="已订阅GitHub项目"
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
    demo.launch(share=False, debug=True)
