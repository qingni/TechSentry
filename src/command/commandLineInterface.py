from config import Config
from scheduler import Scheduler
from github_api import GitHubAPI
from notifier import Notifier
from report_generator import ReportGenerator
from subscription import SubscriptionManager
import threading
from typing import Callable, Dict
from llm import LLM
class CommandLineInterface:
    """命令行界面类，封装所有交互逻辑"""
    
    def __init__(self):
        config = Config()
        self.config = config
        self.github_api = GitHubAPI(config.github_token)
        self.notifier = Notifier(config.notification_settings)
        llm = LLM()
        self.report_generator = ReportGenerator(llm)
        self.subscription_manager = SubscriptionManager(config.subscriptions_file)
        
        # 初始化调度器
        self.scheduler = Scheduler(
            github_api=self.github_api,
            subscription_manager=self.subscription_manager,
            notifier=self.notifier,
            report_generator=self.report_generator,
            interval=config.update_interval
        )
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # 命令注册
        self.commands: Dict[str, Callable] = {
            'add': self.add_subscription,
            'remove': self.remove_subscription,
            'list': self.list_subscriptions,
            'fetch': self.fetch_updates,
            'help': self.print_help,
            'export': self.export_daily_progress,
            'generate': self.generate_daily_report,
            'exit': self.exit_tool,
            'quit': self.exit_tool
        }
    
    def _run_scheduler(self):
        """运行调度器"""
        self.scheduler.start()
    
    def add_subscription(self, repo: str):
        """添加订阅"""
        self.subscription_manager.add_subscription(repo)
        print(f"✓ 已添加订阅: {repo}")
    
    def remove_subscription(self, repo: str):
        """移除订阅"""
        self.subscription_manager.remove_subscription(repo)
        print(f"✓ 已移除订阅: {repo}")
    
    def list_subscriptions(self):
        """列出所有订阅"""
        subscriptions = self.subscription_manager.get_subscriptions()
        print("当前订阅:")
        for sub in subscriptions:
            print(f"  - {sub}")
    
    def fetch_updates(self):
        """立即获取更新"""
        for repo in subscriptions:
            print(f"正在检查 {repo} 的更新...")
            updates = self.github_api.fetch_updates(repo)
            markdown = self.report_generator.export_daily_progress(repo, updates)
            self.report_generator.generate_daily_report(markdown)
        print("✓ 更新获取完成:")
    
    def export_daily_progress(self, repo):
        """导出每日进度"""
        self.github_api.export_repo_daily_progress(repo)
            
    def generate_daily_report(self, file):
        """生成每日报告"""
        self.report_generator.generate_daily_report(file)

    def print_help(self):
        """显示帮助信息"""
        help_text = """
GitHub Argus 命令行工具

可用命令:
  add <repo>       添加订阅 (例如: owner/repo)
  remove <repo>    移除订阅 (例如: owner/repo)
  list             列出所有订阅
  fetch            立即获取更新
  export <repo>    导出每日进度
  generate <file>  生成每日报告
  help             显示帮助信息
  exit/quit        退出工具
"""
        print(help_text)
    
    def exit_tool(self):
        """退出工具"""
        print("正在退出 GitHub Argus...")
        self.scheduler.stop()
        self.scheduler_thread.join(timeout=5)
        print("✓ 已安全退出")
        exit(0)
    
    def execute_command(self, command: str, args: list):
        """执行命令"""
        try:
            if command in self.commands:
                # 处理带参数的命令
                if command in ['add', 'remove', 'export', 'generate'] and not args:
                    print(f"错误: '{command}' 命令需要参数")
                    return
                
                # 执行命令
                if command in ['add', 'remove', 'export', 'generate']:
                    self.commands[command](args[0])
                else:
                    self.commands[command]()
            else:
                print(f"未知命令: {command}")
                self.print_help()
        except Exception as e:
            print(f"执行命令时出错: {str(e)}")

