from config import Config
from github_api import GitHubAPI
from notifier import Notifier
from report_generator import ReportGenerator
from subscription import SubscriptionManager
from typing import Callable, Dict, Optional
from llm import LLM

class CommandInterface:
    """命令行界面类，封装所有交互逻辑"""
    
    def __init__(self):
        config = Config()
        self.config = config
        self.github_api = GitHubAPI(config.github_token)
        self.notifier = Notifier(config.notification_settings)
        llm = LLM(config)
        self.report_generator = ReportGenerator(llm, config.report_types)
        self.subscription_manager = SubscriptionManager(config.subscriptions_file)
    
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
        
    def add_subscription(self, repo: str):
        """添加订阅"""
        self.subscription_manager.add_subscription(repo)
        print(f"✓ 已添加订阅: {repo}")
    
    def remove_subscription(self, repo: str):
        """移除订阅"""
        if self.subscription_manager.remove_subscription(repo):
            print(f"✓ 已移除订阅: {repo}")
        else:
            print(f"✗ 未找到订阅: {repo}")
    
    def list_subscriptions(self):
        """列出所有订阅"""
        subscriptions = self.subscription_manager.get_subscriptions()
        if subscriptions:
            print("当前订阅:")
            for sub in subscriptions:
                print(f"  - {sub}")
        else:
            print("暂无订阅，可使用 'add <repo>' 命令添加")
    
    def fetch_updates(self):
        """立即获取更新"""
        subscriptions = self.subscription_manager.get_subscriptions()
        if not subscriptions:
            print("暂无订阅，无法获取更新")
            return
            
        for repo in subscriptions:
            print(f"正在检查 {repo} 的更新...")
            updates = self.github_api.fetch_updates(repo)
            if updates:
                markdown = self.github_api.export_daily_progress(repo, updates)
                self.report_generator.generate_github_daily_report(markdown)
            else:
                print(f"  {repo} 暂无新更新")
        print("✓ 更新获取完成")
    
    def export_daily_progress(self, repo: str, since: Optional[str] = None, 
                             until: Optional[str] = None, relative: Optional[str] = None):
        """导出每日进度，支持时间范围参数"""
        # 验证时间参数冲突
        if relative and (since or until):
            print("警告: 相对时间(relative)将优先于绝对时间(since/until)")
        
        print(f"export_daily_progress----", repo, since, until, relative)
        updates = self.github_api.fetch_updates(repo)
        if updates:
            self.github_api.export_daily_progress(
                repo=repo,
                updates=updates,
                since=since,
                until=until,
                relative=relative
            )
            print(f"✓ 已导出 {repo} 的进度数据")
    
    def generate_daily_report(self, file: str):
        """生成每日报告到指定文件"""
        self.report_generator.generate_github_daily_report(file)
        print(f"✓ 每日报告已生成至: {file}")

    def print_help(self):
        """显示帮助信息"""
        help_text = """
Tech Sentry 命令行工具

可用命令:
  add <repo>                  添加订阅
    参数:
      --repo      GitHub仓库路径 (格式: owner/repo)
    示例:
      add --repo=langchain-ai/langchain
      
  remove <repo>               移除订阅
    参数:
      --repo      已订阅的仓库路径 (格式: owner/repo)
    示例:
      remove --repo=langchain-ai/langchain
      
  list                        列出所有订阅
    示例:
      list
      
  fetch                       立即获取所有订阅仓库的更新
    示例:
      fetch
      
  export <repo> [since] [until] [relative]  导出指定仓库的每日进度
    参数:
      --repo        仓库路径 (格式: owner/repo，必填)
      --since       起始日期 (格式: YYYY-MM-DD，可选)
      --until       结束日期 (格式: YYYY-MM-DD，可选)
      --relative    相对时间 (例如: 24hours, 7d，可选)
    说明:
      时间参数优先级: relative > since/until，不指定则默认今天
    示例:
      export --repo=langchain-ai/langchain --since="" --until="" --relative=7d       # 过去7天
      
  generate <file>             生成每日报告到指定文件
    参数:
      --file        输出文件路径 (例如: ./report.md)
    示例:
      generate --file=./daily_report.md
      
  help                        显示帮助信息
  
  exit/quit                   退出工具
"""
        print(help_text)
    
    def exit_tool(self):
        """退出工具"""
        print("正在退出 Tech Sentry...")
        print("✓ 已安全退出")
        exit(0)
    
    def execute_command(self, command: str, args) -> None:
        """执行命令，适配无--前缀的参数格式"""
        try:
            if command not in self.commands:
                print(f"未知命令: {command}")
                self.print_help()
                return

            # 处理add命令
            if command == 'add':
                self.commands[command](args.repo)

            # 处理remove命令
            elif command == 'remove':
                self.commands[command](args.repo)

            # 处理export命令（支持可选的时间参数）
            elif command == 'export':
                # 传递所有参数，None会被自动处理
                print(f"export_daily_progress: {args}")
                self.commands[command](
                    repo=args.repo,
                    since=args.since,
                    until=args.until,
                    relative=args.relative
                )

            # 处理generate命令
            elif command == 'generate':
                self.commands[command](args.file)

            # 无参数命令
            else:
                self.commands[command]()

        except Exception as e:
            print(f"执行命令时出错: {str(e)}")
    