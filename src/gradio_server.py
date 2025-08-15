import gradio as gr
from subscription import SubscriptionManager
from config import Config
from llm import LLM
from github_api import GitHubAPI
from report_generator import ReportGenerator
from utils import Utils

config = Config()
github_api = GitHubAPI(config.github_token)
llm = LLM()
report_generator = ReportGenerator(llm)
subscription_manager = SubscriptionManager(config.subscriptions_file)

def export_progress_by_data_range(repo, relative):
    relative_time = Utils.get_key_by_description(relative)
    updates = github_api.fetch_updates(repo, relative=relative_time)
    markdown = report_generator.export_daily_progress(repo, updates, relative=relative_time)
    report, report_file_path = report_generator.generate_daily_report(markdown)
    
    # 修改返回类型为字符串
    return report, report_file_path

demo = gr.Interface(
  fn=export_progress_by_data_range,
  title="GitHubArgus",
  inputs=[
    gr.Dropdown(subscription_manager.get_subscriptions(), label="订阅管理", info="已订阅的仓库"),
    gr.Dropdown(Utils.get_all_relative_time_descriptions(), label="时间范围", info="选择时间范围")
  ],
  outputs=[gr.Markdown(), gr.File(label="下载报告")]
)

if __name__ == "__main__":
    demo.launch(share=False)
    # 可选带有用户认证的启动方式
    # demo.launch(share=False, server_name="0.0.0.0", auth=("argus", "123456"))

