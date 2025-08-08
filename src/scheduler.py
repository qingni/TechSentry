import time

class Scheduler:
    def __init__(self, github_api, subscription_manager, notifier, report_generator, interval):
        self.github_api = github_api
        self.subscription_manager = subscription_manager
        self.notifier = notifier
        self.report_generator = report_generator
        self.interval = interval
        self.running = False  # 添加运行状态标志

    def check_for_updates(self):
        subscriptions = self.subscription_manager.get_subscriptions()
        
        for repo in subscriptions:
            print(f"正在检查 {repo} 的更新...")
            updates = self.github_api.fetch_updates(repo)
            markdown = self.report_generator.export_daily_progress(repo, updates)
            self.report_generator.generate_daily_report(markdown)


    def start(self):
        self.running = True  # 设置运行状态
        while self.running:  # 检查运行状态
            # self.check_for_updates()
            # 使用可中断的sleep
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        """停止调度器"""
        self.running = False  # 设置停止标志
