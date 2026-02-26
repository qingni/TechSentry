from config import Config
from github_api import GitHubAPI
from report_generator import ReportGenerator
from subscription import SubscriptionManager
from llm import LLM
# import schedule
import time  # 导入time库，用于控制时间间隔
from logger import LOG
from notifier import Notifier
from hackernews_api import HackerNewsAPI
from github_trend_api import GithubTrendAPI
import signal
import sys
from cleanup_reports import CleanReportsDir
import threading
from datetime import datetime
import psutil  # 添加资源监控库
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR  # 添加调度事件
import os  # 添加os模块导入
from apscheduler.schedulers.background import BackgroundScheduler  # 添加正确的调度器导入

# 添加全局API计数器
api_call_counter = {
    "github": 0,
    "hackernews": 0,
    "github_trend": 0
}
api_counter_lock = threading.Lock()

# 添加全局任务执行偏差记录
task_deviations = []
task_deviation_lock = threading.Lock()

# 添加全局资源监控记录
resource_stats = {
    "memory": [],
    "cpu": []
}
resource_lock = threading.Lock()

# 添加全局调度器引用
scheduler = None

def graceful_shutdown(signum=None, frame=None, exit_code=0):
    """统一关闭处理函数"""
    global scheduler
    
    signal_name = "终止信号" if signum is None else f"信号 {signal.Signals(signum).name}"
    LOG.info(f"守护进程接收到{signal_name}，正在优雅关闭...")
    
    if scheduler:
        LOG.info("正在关闭调度器...")
        scheduler.shutdown()
        LOG.info("调度器已关闭")
    
    sys.exit(exit_code)

def record_task_deviation(event):
    """记录任务执行时间偏差，兼容APScheduler 3.x的事件类型"""
    # 确定事件类型并获取实际执行时间
    if hasattr(event, 'executed_time'):
        # 处理JobExecutionEvent（任务成功执行）
        actual_time = event.executed_time
    elif hasattr(event, 'exception'):
        # 处理JobErrorEvent（任务执行出错）
        actual_time = event.scheduled_run_time  # 错误事件使用计划时间作为参考
    else:
        LOG.warning("未知的任务事件类型，无法计算偏差")
        return
    
    # 检查计划执行时间是否存在
    if not hasattr(event, 'scheduled_run_time'):
        LOG.warning("任务事件缺少计划执行时间属性，无法计算偏差")
        return
    
    # 计算偏差（秒）
    deviation = (actual_time - event.scheduled_run_time).total_seconds()
    
    with task_deviation_lock:
        task_deviations.append(deviation)
        
        # 当累积500条记录时计算平均偏差
        if len(task_deviations) >= 500:
            avg_deviation = sum(task_deviations) / len(task_deviations)
            LOG.info(f"[任务执行偏差] 基于{len(task_deviations)}次执行，平均偏差: {avg_deviation:.2f}秒")
            # 写入日志文件
            with open("logs/task_deviation.log", "a") as f:
                f.write(f"{datetime.now()},{avg_deviation}\n")
            task_deviations.clear()


def monitor_resources():
    """记录系统资源使用情况"""
    process = psutil.Process(os.getpid())
    mem_usage = process.memory_info().rss / (1024 * 1024)  # 转换为MB
    cpu_usage = process.cpu_percent(interval=1)
    
    with resource_lock:
        resource_stats["memory"].append(mem_usage)
        resource_stats["cpu"].append(cpu_usage)
        
        # 保持最近30天的数据（30天*24小时*60分钟）
        max_entries = 30 * 24 * 60
        for key in resource_stats:
            if len(resource_stats[key]) > max_entries:
                resource_stats[key] = resource_stats[key][-max_entries:]

def calculate_resource_avg():
    """计算资源使用月平均值"""
    with resource_lock:
        if not resource_stats["memory"] or not resource_stats["cpu"]:
            return
            
        avg_memory = sum(resource_stats["memory"]) / len(resource_stats["memory"])
        avg_cpu = sum(resource_stats["cpu"]) / len(resource_stats["cpu"])
        
        LOG.info(f"[资源统计] 内存平均使用: {avg_memory:.2f}MB, CPU平均使用: {avg_cpu:.2f}%")
        # 写入日志文件
        with open("logs/resource_stats.log", "a") as f:
            f.write(f"{datetime.now()},{avg_memory:.2f},{avg_cpu:.2f}\n")
        
        # 清空记录开始新周期
        resource_stats["memory"] = []
        resource_stats["cpu"] = []

def github_job(github_api, subscription_manager, report_generator, notifier, days):
    """
    gibhub订阅仓库进展任务
    """
    LOG.info("[开始执行github定时任务]")
    subscriptions = subscription_manager.get_subscriptions()
    LOG.info(f"github订阅列表：{subscriptions}")     
    
    # 更新API计数器
    with api_counter_lock:
        api_call_counter["github"] += len(subscriptions)
    
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
    
    # 更新API计数器
    with api_counter_lock:
        api_call_counter["hackernews"] += 1
    
    stories = hack_news_api.get_hackernews_latest()
    markdown_file_path = hack_news_api.export_hours_hack_news(stories)
    report_generator.generate_hack_news_hours_report(markdown_file_path)
    LOG.info(f"[hacknews hours定时任务执行完毕]")

def hack_news_daily_job(hack_news_api, report_generator, notifier):
    """
    hacknews每日热点任务
    """
    LOG.info("[开始执行hacknews daily定时任务]")
    # 更新API计数器
    with api_counter_lock:
        api_call_counter["hackernews"] += 1
    markdown_file_path = hack_news_api.generate_daily_report()
    report, report_file_path = report_generator.generate_hack_news_daily_report(markdown_file_path)
    notifier.notify_hack_news_daily(report)
    LOG.info(f"[hacknews daily定时任务执行完毕]")

def github_trend_daily_job(github_trend_api, report_generator, notifier):
    """
    github trend每日任务
    """
    LOG.info("[开始执行github trend定时任务]")
    # 更新API计数器
    with api_counter_lock:
        api_call_counter["github_trend"] += 1
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

def record_api_stats():
    """记录API统计到日志"""
    with api_counter_lock:
        stats = api_call_counter.copy()
        # 重置计数器
        api_call_counter["github"] = 0
        api_call_counter["hackernews"] = 0
        api_call_counter["github_trend"] = 0
    
    total = sum(stats.values())
    log_msg = (
        f"[API统计] 日期:{time.strftime('%Y-%m-%d')} "
        f"GitHub调用:{stats['github']} "
        f"HackerNews调用:{stats['hackernews']} "
        f"GitHub趋势调用:{stats['github_trend']} "
        f"总计:{total}"
    )
    LOG.info(log_msg)
    
    # 写入持久化日志
    with open("logs/api_stats.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d')},{stats['github']},{stats['hackernews']},{stats['github_trend']},{total}\n")

def main():
    global scheduler
    
    # 注册信号处理
    signal.signal(signal.SIGTERM, graceful_shutdown)  # kill命令
    signal.signal(signal.SIGINT, lambda s, f: graceful_shutdown(s, f, 0))  # Ctrl+C

    config = Config()
    github_api = GitHubAPI(config.github_token)
    llm = LLM(config)
    report_generator = ReportGenerator(llm, config.report_types)
    subscription_manager = SubscriptionManager(config.subscriptions_file)
    notifier = Notifier(config.notification_settings)
    hack_news_api = HackerNewsAPI()
    github_trend_api = GithubTrendAPI()
    clean_reports = CleanReportsDir()
    
    # 获取调度器实例
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # 添加任务执行事件监听
    scheduler.add_listener(record_task_deviation, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # 1. 清理报告目录任务（每天00:00）
    scheduler.add_job(
        clean_report_dir_job,
        'cron',
        hour=0,
        minute=0,
        args=[clean_reports],  # 传递参数
        timezone='Asia/Shanghai'
    )

    # 2. API统计定时任务（每天00:00）
    scheduler.add_job(
        record_api_stats,
        'cron',
        hour=0,
        minute=0,
        timezone='Asia/Shanghai'
    )

    # 3. GitHub相关任务（每隔config.update_freq_days天，在指定时间执行）
    # github_job(github_api, subscription_manager, report_generator, notifier, config.update_freq_days)
    
    # 解析配置中的时间和间隔天数
    hour, minute = map(int, config.update_execution_time.split(':'))
    interval_days = config.update_freq_days  # 从配置获取间隔天数（例如1天）

    # 添加定时任务，每隔interval_days天的指定时间执行
    scheduler.add_job(
        github_job,
        'cron',
        # 每隔interval_days天，在指定的时分秒执行
        day=f"*/{interval_days}",  # 关键配置：每隔N天
        hour=hour,
        minute=minute,
        second=0,
        args=[github_api, subscription_manager, report_generator, notifier, interval_days],
        misfire_grace_time=600,  # 允许10分钟的延迟缓冲
        timezone='Asia/Shanghai'  # 显式指定时区，避免时区问题导致的时间偏差
    )

    # 4. HackNews小时级任务（每4小时，在整点执行）
    # hack_news_hours_job(hack_news_api, report_generator, notifier)
    scheduler.add_job(
        hack_news_hours_job,
        'cron',
        hour='*/4',  # 每4小时
        minute=0,
        misfire_grace_time=300,  # 允许5分钟的延迟
        args=[hack_news_api, report_generator, notifier],
        timezone='Asia/Shanghai'
    )

    # 5. HackNews每日任务（每天20:00）
    # hack_news_daily_job(hack_news_api, report_generator, notifier)
    scheduler.add_job(
        hack_news_daily_job,
        'cron',
        hour=20,
        minute=0,
        args=[hack_news_api, report_generator, notifier],
        timezone='Asia/Shanghai'
    )

    # 6. GitHub趋势每日任务（每天18:00）
    # github_trend_daily_job(github_trend_api, report_generator, notifier)
    scheduler.add_job(
        github_trend_daily_job,
        'cron',
        hour=18,
        minute=0,
        args=[github_trend_api, report_generator, notifier],
        timezone='Asia/Shanghai'
    )
    # 7. 资源监控任务（每分钟执行）
    # scheduler.add_job(
    #     monitor_resources,
    #     'interval',
    #     minutes=1,
    #     timezone='Asia/Shanghai'
    # )
    # 8.添加资源平均值计算任务（每月1号执行）
    # scheduler.add_job(
    #   calculate_resource_avg,
    #   'cron',
    #   day=1,  # 每月1号
    #   hour=0,
    #   minute=5,
    #   timezone='Asia/Shanghai'
    # )
    
    # --------------------------
    # 主循环
    # --------------------------
    try:
        # 只需保持主进程不退出即可
        while True:
            time.sleep(2)
    except Exception as e:
        LOG.error(f"主进程发生未捕获异常: {str(e)}")
        graceful_shutdown(exit_code=1)
    
    # 正常退出时也调用关闭流程
    graceful_shutdown(exit_code=0)
    
if __name__ == "__main__":
    main()