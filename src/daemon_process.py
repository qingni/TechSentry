from config import Config
from scheduler import Scheduler
from github_api import GitHubAPI
from notifier import Notifier
from report_generator import ReportGenerator
from subscription import SubscriptionManager
import threading
from llm import LLM
import daemon
import time  # 导入time库，用于控制时间间隔

def _run_scheduler(scheduler):
  """运行调度器"""
  scheduler.start()

def main():
  config = Config()
  config = config
  github_api = GitHubAPI(config.github_token)
  notifier = Notifier(config.notification_settings)
  llm = LLM()
  report_generator = ReportGenerator(llm)
  subscription_manager = SubscriptionManager(config.subscriptions_file)
        
  # 初始化调度器
  scheduler = Scheduler(
    github_api=github_api,
    subscription_manager=subscription_manager,
    notifier=notifier,
    report_generator=report_generator,
    interval=config.update_interval,
  )
        
  # 启动调度器线程
  scheduler_thread = threading.Thread(target=_run_scheduler, args=(scheduler,))
  scheduler_thread.daemon = True
  scheduler_thread.start()
  
  # 使用python-daemon库，以守护进程方式运行程序
  with daemon.DaemonContext():
    try:
      while True:
        time.sleep(config.update_interval)  # 按配置的更新间隔休眠
    except KeyboardInterrupt:
      LOG.info("Daemon process stopped.")  # 在接收到中断信号时记录日志
  
if __name__ == "__main__":
    main()  
  