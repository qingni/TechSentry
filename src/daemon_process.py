from config import Config
from github_api import GitHubAPI
from report_generator import ReportGenerator
from subscription import SubscriptionManager
from llm import LLM
import schedule
import time  # 导入time库，用于控制时间间隔
from logger import LOG
from notifier import Notifier
import signal
import sys

def graceful_shutdown(signum, frame):
    LOG.info("守护进程接收到终止信号，正在优雅关闭...")
    sys.exit(0)

def github_job(github_api, subscription_manager, report_generator, notifier, days):
  LOG.info("[开始执行定时任务]")
  subscriptions = subscription_manager.get_subscriptions()
  LOG.info(f"订阅列表：{subscriptions}")      
  for repo in subscriptions:
    updates = github_api.fetch_updates(repo, relative=days)
    markdown = github_api.export_daily_progress(repo, updates, relative=days)
    report, report_file_path = report_generator.generate_daily_report(markdown)
    notifier.notify(repo, report)
  LOG.info(f"[定时任务执行完毕]")

def main():
  signal.signal(signal.SIGTERM, graceful_shutdown)
  
  config = Config()
  github_api = GitHubAPI(config.github_token)
  llm = LLM(config)
  report_generator = ReportGenerator(llm)
  subscription_manager = SubscriptionManager(config.subscriptions_file)
  notifier = Notifier(config.notification_settings)
  
  github_job(github_api, subscription_manager, report_generator, notifier, config.update_freq_days)
  
  schedule.every(config.update_freq_days).days.at(
    config.update_execution_time
  ).do(github_job, github_api, subscription_manager, report_generator, notifier, config.update_freq_days)
  
  try:
    while True:
      schedule.run_pending()
      time.sleep(1)  # 短暂休眠，避免CPU占用过高
  except Exception as e:
    LOG.error(f"主进程发生异常: {str(e)}")  # 在接收到中断信号时记录日志
    sys.exit(1)
  
if __name__ == "__main__":
    main()  
  