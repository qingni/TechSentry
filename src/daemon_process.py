from config import Config
from github_api import GitHubAPI
from report_generator import ReportGenerator
from subscription import SubscriptionManager
from llm import LLM
import schedule
import time  # 导入time库，用于控制时间间隔
from logger import LOG
from notifier import Notifier
from hackernews_api import HackerNewsAPI
from github_trend_api import GithubTrendAPI
import signal
import sys
from cleanup_reports import CleanReportsDir

def graceful_shutdown(signum, frame):
    LOG.info("守护进程接收到终止信号，正在优雅关闭...")
    sys.exit(0)

def github_job(github_api, subscription_manager, report_generator, notifier, days):
  """
  gibhub订阅仓库进展任务
  """
  LOG.info("[开始执行github定时任务]")
  subscriptions = subscription_manager.get_subscriptions()
  LOG.info(f"github订阅列表：{subscriptions}")      
  for repo in subscriptions:
    updates = github_api.fetch_updates(repo, relative=days)
    markdown = github_api.export_daily_progress(repo, updates, relative=days)
    report, report_file_path = report_generator.generate_github_daily_report(markdown)
    notifier.notify_github(repo, report)
  LOG.info(f"[github定时任务执行完毕]")

def hack_news_hours_job(hack_news_api, report_generator, notifier):
  """
  hacknews小时级热点任务
  """
  LOG.info("[开始执行hacknews hours定时任务]")
  stories = hack_news_api.get_hackernews_latest()
  markdown_file_path = hack_news_api.export_hours_hack_news(stories)
  report_generator.generate_hack_news_hours_report(markdown_file_path)
  LOG.info(f"[hacknews hours定时任务执行完毕]")

def hack_news_daily_job(hack_news_api, report_generator, notifier):
  """
  hacknews每日热点任务
  """
  LOG.info("[开始执行hacknews daily定时任务]")
  markdown_file_path = hack_news_api.generate_daily_report()
  report, report_file_path = report_generator.generate_hack_news_daily_report(markdown_file_path)
  notifier.notify_hack_news_daily(report)
  LOG.info(f"[hacknews daily定时任务执行完毕]")

def github_trend_daily_job(github_trend_api, report_generator, notifier):
  """
  github trend每日任务
  """
  LOG.info("[开始执行github trend定时任务]")
  repos = github_trend_api.get_github_trending()
  markdown_file_path = github_trend_api.generate_daily_github_trend(repos)
  report, report_file_path = report_generator.generate_github_trend_daily_report(markdown_file_path)
  print(f"生成github trend日报: {report}")
  notifier.notify_github_trend(report)
  LOG.info(f"[github trend定时任务执行完毕]")

def clean_report_dir_job(clean_reports):
  """
  清理报告目录任务
  """
  clean_reports.clean_all_report_dir()

def main():
  signal.signal(signal.SIGTERM, graceful_shutdown)
  
  config = Config()
  github_api = GitHubAPI(config.github_token)
  llm = LLM(config)
  report_generator = ReportGenerator(llm, config.report_types)
  subscription_manager = SubscriptionManager(config.subscriptions_file)
  notifier = Notifier(config.notification_settings)
  hack_news_api = HackerNewsAPI()
  github_trend_api = GithubTrendAPI()
  clean_reports = CleanReportsDir()
  
  # 清理报告目录任务
  schedule.every().day.at("00:00").do(clean_report_dir_job, clean_reports)
  
  # github_job(github_api, subscription_manager, report_generator, notifier, config.update_freq_days)
  schedule.every(config.update_freq_days).days.at(
    config.update_execution_time
  ).do(github_job, github_api, subscription_manager, report_generator, notifier, config.update_freq_days)
  
  # hack_news_hours_job(hack_news_api, report_generator, notifier)
  schedule.every(4).hours.at(":00").do(hack_news_hours_job, hack_news_api, report_generator, notifier)
  
  # hack_news_daily_job(hack_news_api, report_generator, notifier)
  schedule.every().day.at("20:00").do(hack_news_daily_job, hack_news_api, report_generator, notifier)
  
  # github_trend_daily_job(github_trend_api, report_generator, notifier)
  schedule.every().day.at("18:00").do(github_trend_daily_job, github_trend_api, report_generator, notifier)
  
  try:
    while True:
      schedule.run_pending()
      time.sleep(1)  # 短暂休眠，避免CPU占用过高
  except Exception as e:
    LOG.error(f"主进程发生异常: {str(e)}")  # 在接收到中断信号时记录日志
    sys.exit(1)
  
if __name__ == "__main__":
    main()  
  