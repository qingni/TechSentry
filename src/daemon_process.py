from config import Config
from github_api import GitHubAPI
from report_generator import ReportGenerator
from subscription import SubscriptionManager
from llm import LLM
# import schedule
import time  # 导入time库，用于控制时间间隔
import json
from logger import LOG
from notifier import Notifier
from hackernews_api import HackerNewsAPI
from github_trend_api import GithubTrendAPI
import signal
import sys
from cleanup_reports import CleanReportsDir
from dashboard import generate_weekly_dashboard
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.events import EVENT_JOB_SUBMITTED, EVENT_JOB_EXECUTED, EVENT_JOB_ERROR  # 调度事件
import os
from apscheduler.schedulers.background import BackgroundScheduler

# 全局API计数器（按天落盘）
api_call_counter = {
    "github": 0,
    "hackernews": 0,
    "github_trend": 0
}
api_counter_lock = threading.Lock()

# 任务运行时追踪（用于统计任务耗时）
job_runtime_tracker = {}
job_runtime_lock = threading.Lock()

MAX_SAMPLE_SIZE = 5000
ON_TIME_THRESHOLD_SECONDS = 60.0


def _new_job_metrics():
    return {
        "total_runs": 0,
        "success_runs": 0,
        "failed_runs": 0,
        "duration_samples": [],
        "deviation_samples": []
    }


def _new_source_metrics():
    return {
        "attempts": 0,
        "success": 0,
        "failure": 0,
        "report_success": 0,
        "report_failure": 0,
        "notify_success": 0,
        "notify_failure": 0,
        "last_success_at": None
    }


# 任务级KPI统计
job_kpi = {
    "scheduler": _new_job_metrics(),
    "jobs": {}
}
job_kpi_lock = threading.Lock()

# 数据源健康度统计（采集成功率、报告成功率、通知成功率、数据新鲜度）
source_kpi = {
    "github": _new_source_metrics(),
    "hackernews": _new_source_metrics(),
    "github_trend": _new_source_metrics()
}
source_kpi_lock = threading.Lock()

# 添加全局调度器引用
scheduler = None
shutdown_in_progress = False

# 统一时区与日志目录
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

API_STATS_LOG = os.path.join(LOG_DIR, "api_stats.log")
JOB_KPI_LOG = os.path.join(LOG_DIR, "job_kpi.log")
SOURCE_HEALTH_LOG = os.path.join(LOG_DIR, "source_health.log")


def _append_sample(samples, value):
    samples.append(value)
    if len(samples) > MAX_SAMPLE_SIZE:
        del samples[:len(samples) - MAX_SAMPLE_SIZE]


def _ensure_job_kpi_locked(job_id):
    if job_id not in job_kpi["jobs"]:
        job_kpi["jobs"][job_id] = _new_job_metrics()
    return job_kpi["jobs"][job_id]


def _safe_rate(numerator, denominator):
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _percentile(samples, q):
    if not samples:
        return None

    ordered = sorted(samples)
    if len(ordered) == 1:
        return round(ordered[0], 2)

    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    weight = pos - lower
    value = ordered[lower] * (1 - weight) + ordered[upper] * weight
    return round(value, 2)


def _summarize_job_stats(stats):
    deviation_samples = list(stats["deviation_samples"])
    duration_samples = list(stats["duration_samples"])

    on_time_runs = sum(1 for d in deviation_samples if abs(d) <= ON_TIME_THRESHOLD_SECONDS)

    avg_deviation = None
    if deviation_samples:
        avg_deviation = round(sum(deviation_samples) / len(deviation_samples), 2)

    max_abs_deviation = None
    if deviation_samples:
        max_abs_deviation = round(max(abs(d) for d in deviation_samples), 2)

    avg_duration = None
    if duration_samples:
        avg_duration = round(sum(duration_samples) / len(duration_samples), 2)

    return {
        "total_runs": stats["total_runs"],
        "success_runs": stats["success_runs"],
        "failed_runs": stats["failed_runs"],
        "success_rate_pct": _safe_rate(stats["success_runs"], stats["total_runs"]),
        "on_time_runs": on_time_runs,
        "on_time_rate_pct": _safe_rate(on_time_runs, len(deviation_samples)),
        "avg_deviation_sec": avg_deviation,
        "max_abs_deviation_sec": max_abs_deviation,
        "avg_duration_sec": avg_duration,
        "p95_duration_sec": _percentile(duration_samples, 0.95),
        "deviation_sample_count": len(deviation_samples),
        "duration_sample_count": len(duration_samples)
    }


def _mark_job_start(job_id):
    with job_runtime_lock:
        job_runtime_tracker[job_id] = time.perf_counter()


def _mark_job_end(job_id, success):
    with job_runtime_lock:
        start_point = job_runtime_tracker.pop(job_id, None)

    duration = None
    if start_point is not None:
        duration = time.perf_counter() - start_point

    with job_kpi_lock:
        scheduler_stats = job_kpi["scheduler"]
        scheduler_stats["total_runs"] += 1
        if success:
            scheduler_stats["success_runs"] += 1
        else:
            scheduler_stats["failed_runs"] += 1
        if duration is not None:
            _append_sample(scheduler_stats["duration_samples"], duration)

        job_stats = _ensure_job_kpi_locked(job_id)
        job_stats["total_runs"] += 1
        if success:
            job_stats["success_runs"] += 1
        else:
            job_stats["failed_runs"] += 1
        if duration is not None:
            _append_sample(job_stats["duration_samples"], duration)


def _update_source_kpi(
    source,
    attempts=0,
    success=0,
    failure=0,
    report_success=0,
    report_failure=0,
    notify_success=0,
    notify_failure=0,
    set_last_success=False
):
    with source_kpi_lock:
        stats = source_kpi.setdefault(source, _new_source_metrics())
        stats["attempts"] += attempts
        stats["success"] += success
        stats["failure"] += failure
        stats["report_success"] += report_success
        stats["report_failure"] += report_failure
        stats["notify_success"] += notify_success
        stats["notify_failure"] += notify_failure
        if set_last_success:
            stats["last_success_at"] = datetime.now(SHANGHAI_TZ)


def _build_and_reset_job_kpi_snapshot():
    with job_kpi_lock:
        snapshot = {
            "scheduler": _summarize_job_stats(job_kpi["scheduler"]),
            "jobs": {
                job_id: _summarize_job_stats(job_stats)
                for job_id, job_stats in job_kpi["jobs"].items()
            }
        }
        job_kpi["scheduler"] = _new_job_metrics()
        job_kpi["jobs"] = {}
    return snapshot


def _build_and_reset_source_kpi_snapshot():
    now = datetime.now(SHANGHAI_TZ)
    with source_kpi_lock:
        snapshot = {}
        for source, stats in source_kpi.items():
            report_total = stats["report_success"] + stats["report_failure"]
            notify_total = stats["notify_success"] + stats["notify_failure"]

            freshness_minutes = None
            if stats["last_success_at"] is not None:
                freshness_minutes = round((now - stats["last_success_at"]).total_seconds() / 60, 2)

            snapshot[source] = {
                "attempts": stats["attempts"],
                "success": stats["success"],
                "failure": stats["failure"],
                "collection_success_rate_pct": _safe_rate(stats["success"], stats["attempts"]),
                "report_success": stats["report_success"],
                "report_failure": stats["report_failure"],
                "report_success_rate_pct": _safe_rate(stats["report_success"], report_total),
                "notify_success": stats["notify_success"],
                "notify_failure": stats["notify_failure"],
                "notify_success_rate_pct": _safe_rate(stats["notify_success"], notify_total),
                "last_success_at": stats["last_success_at"].isoformat() if stats["last_success_at"] else None,
                "data_freshness_minutes": freshness_minutes
            }

            last_success_at = stats["last_success_at"]
            source_kpi[source] = _new_source_metrics()
            source_kpi[source]["last_success_at"] = last_success_at

    return snapshot


def _append_json_line(path, data):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def graceful_shutdown(signum=None, frame=None, exit_code=0):
    """统一关闭处理函数"""
    global scheduler, shutdown_in_progress

    if shutdown_in_progress:
        return
    shutdown_in_progress = True

    signal_name = "终止信号" if signum is None else f"信号 {signal.Signals(signum).name}"
    LOG.info(f"守护进程接收到{signal_name}，正在优雅关闭...")

    if scheduler:
        try:
            if getattr(scheduler, "running", False):
                LOG.info("正在关闭调度器...")
                scheduler.shutdown(wait=False)
                LOG.info("调度器已关闭")
        except Exception as e:
            LOG.warning(f"关闭调度器时发生异常: {e}")

    if signum is not None:
        sys.exit(exit_code)

def _record_job_deviation(job_id, scheduled_run_time):
    """记录任务执行时间偏差（实际触发时间 - 计划触发时间）"""
    if scheduled_run_time is None:
        return

    actual_time = datetime.now(SHANGHAI_TZ)
    if scheduled_run_time.tzinfo is None:
        scheduled_time = scheduled_run_time.replace(tzinfo=SHANGHAI_TZ)
    else:
        scheduled_time = scheduled_run_time.astimezone(SHANGHAI_TZ)

    deviation = (actual_time - scheduled_time).total_seconds()

    with job_kpi_lock:
        scheduler_stats = job_kpi["scheduler"]
        _append_sample(scheduler_stats["deviation_samples"], deviation)

        job_stats = _ensure_job_kpi_locked(job_id)
        _append_sample(job_stats["deviation_samples"], deviation)


def on_job_submitted(event):
    """任务提交时记录触发偏差与开始时间"""
    job_id = getattr(event, "job_id", None)
    if not job_id:
        return

    scheduled_times = getattr(event, "scheduled_run_times", None) or []
    if scheduled_times:
        _record_job_deviation(job_id, scheduled_times[0])

    _mark_job_start(job_id)


def on_job_executed(event):
    """任务成功执行后的统计处理"""
    job_id = getattr(event, "job_id", None)
    if not job_id:
        return

    _mark_job_end(job_id, success=True)


def on_job_error(event):
    """任务失败执行后的统计处理"""
    job_id = getattr(event, "job_id", None)
    if not job_id:
        return

    _mark_job_end(job_id, success=False)

    exception = getattr(event, "exception", None)
    if exception is not None:
        LOG.error(f"定时任务执行失败 job_id={job_id}: {exception}")


def flush_kpi_stats():
    """将任务级KPI和数据源健康度按日落盘"""
    snapshot_time = datetime.now(SHANGHAI_TZ)

    job_snapshot = _build_and_reset_job_kpi_snapshot()
    source_snapshot = _build_and_reset_source_kpi_snapshot()

    _append_json_line(
        JOB_KPI_LOG,
        {
            "ts": snapshot_time.isoformat(),
            "tz": "Asia/Shanghai",
            "metrics": job_snapshot
        }
    )

    _append_json_line(
        SOURCE_HEALTH_LOG,
        {
            "ts": snapshot_time.isoformat(),
            "tz": "Asia/Shanghai",
            "metrics": source_snapshot
        }
    )

    scheduler_stats = job_snapshot["scheduler"]
    LOG.info(
        f"[KPI统计] 任务成功率={scheduler_stats.get('success_rate_pct')}% "
        f"准点率={scheduler_stats.get('on_time_rate_pct')}% "
        f"P95耗时={scheduler_stats.get('p95_duration_sec')}s，统计已写入 job_kpi.log/source_health.log"
    )

def github_job(github_api, subscription_manager, report_generator, notifier, days):
    """github订阅仓库进展任务"""
    LOG.info("[开始执行github定时任务]")
    subscriptions = subscription_manager.get_subscriptions()
    LOG.info(f"github订阅列表：{subscriptions}")

    # 更新API计数器
    with api_counter_lock:
        api_call_counter["github"] += len(subscriptions)

    for repo in subscriptions:
        _update_source_kpi("github", attempts=1)

        updates = None
        markdown = None
        try:
            updates = github_api.fetch_updates(repo, relative=days)
            markdown = github_api.export_daily_progress(repo, updates, relative=days)
            _update_source_kpi("github", success=1, set_last_success=True)
        except Exception as e:
            _update_source_kpi("github", failure=1)
            LOG.exception(f"获取仓库{repo}更新失败: {e}")
            continue

        report = None
        try:
            report, report_file_path = report_generator.generate_github_daily_report(markdown)
            _update_source_kpi("github", report_success=1)
        except Exception as e:
            _update_source_kpi("github", report_failure=1)
            LOG.exception(f"生成仓库{repo}报告失败: {e}")
            continue

        try:
            notifier.notify_github(repo, report)
            _update_source_kpi("github", notify_success=1)
        except Exception as e:
            _update_source_kpi("github", notify_failure=1)
            LOG.exception(f"发送仓库{repo}通知失败: {e}")

    LOG.info("[github定时任务执行完毕]")

def hack_news_hours_job(hack_news_api, report_generator, notifier):
    """
    hacknews小时级热点任务
    """
    LOG.info("[开始执行hacknews hours定时任务]")

    # 更新API计数器
    with api_counter_lock:
        api_call_counter["hackernews"] += 1

    _update_source_kpi("hackernews", attempts=1)

    markdown_file_path = None
    try:
        stories = hack_news_api.get_hackernews_latest()
        markdown_file_path = hack_news_api.export_hours_hack_news(stories)
        _update_source_kpi("hackernews", success=1, set_last_success=True)
    except Exception as e:
        _update_source_kpi("hackernews", failure=1)
        LOG.exception(f"hacknews小时任务采集失败: {e}")
        return

    try:
        report_generator.generate_hack_news_hours_report(markdown_file_path)
        _update_source_kpi("hackernews", report_success=1)
    except Exception as e:
        _update_source_kpi("hackernews", report_failure=1)
        LOG.exception(f"hacknews小时任务报告生成失败: {e}")

    LOG.info("[hacknews hours定时任务执行完毕]")

def hack_news_daily_job(hack_news_api, report_generator, notifier):
    """
    hacknews每日热点任务
    """
    LOG.info("[开始执行hacknews daily定时任务]")

    # 更新API计数器
    with api_counter_lock:
        api_call_counter["hackernews"] += 1

    _update_source_kpi("hackernews", attempts=1)

    # ---- 步骤1: 聚合小时报告 ----
    t_step1_start = time.time()
    markdown_file_path = None
    try:
        markdown_file_path = hack_news_api.generate_daily_report()
        _update_source_kpi("hackernews", success=1, set_last_success=True)
    except Exception as e:
        _update_source_kpi("hackernews", failure=1)
        LOG.exception(f"hacknews每日任务采集失败: {e}")
        return
    t_step1 = time.time() - t_step1_start

    # ---- 步骤2: LLM 生成日报 ----
    t_step2_start = time.time()
    report = None
    try:
        report, report_file_path = report_generator.generate_hack_news_daily_report(markdown_file_path)
        _update_source_kpi("hackernews", report_success=1)
    except Exception as e:
        _update_source_kpi("hackernews", report_failure=1)
        LOG.exception(f"hacknews每日任务报告生成失败: {e}")
        return
    t_step2 = time.time() - t_step2_start

    # ---- 步骤3: 通知推送 ----
    t_step3_start = time.time()
    try:
        notifier.notify_hack_news_daily(report)
        _update_source_kpi("hackernews", notify_success=1)
    except Exception as e:
        _update_source_kpi("hackernews", notify_failure=1)
        LOG.exception(f"hacknews每日任务通知失败: {e}")
    t_step3 = time.time() - t_step3_start

    t_total = t_step1 + t_step2 + t_step3
    LOG.info(f"[hack_news_daily] 耗时明细 | 聚合: {t_step1:.1f}s | LLM生成: {t_step2:.1f}s | 通知: {t_step3:.1f}s | 总计: {t_total:.1f}s")
    LOG.info("[hacknews daily定时任务执行完毕]")

def github_trend_daily_job(github_trend_api, report_generator, notifier):
    """
    github trend每日任务
    """
    LOG.info("[开始执行github trend定时任务]")

    # 更新API计数器
    with api_counter_lock:
        api_call_counter["github_trend"] += 1

    _update_source_kpi("github_trend", attempts=1)

    markdown_file_path = None
    try:
        repos = github_trend_api.get_github_trending()
        markdown_file_path = github_trend_api.generate_daily_github_trend(repos)
        _update_source_kpi("github_trend", success=1, set_last_success=True)
    except Exception as e:
        _update_source_kpi("github_trend", failure=1)
        LOG.exception(f"github trend任务采集失败: {e}")
        return

    report = None
    try:
        report, report_file_path = report_generator.generate_github_trend_daily_report(markdown_file_path)
        _update_source_kpi("github_trend", report_success=1)
    except Exception as e:
        _update_source_kpi("github_trend", report_failure=1)
        LOG.exception(f"github trend任务报告生成失败: {e}")
        return

    try:
        LOG.info(f"生成github trend日报: {report}")
        notifier.notify_github_trend(report)
        _update_source_kpi("github_trend", notify_success=1)
    except Exception as e:
        _update_source_kpi("github_trend", notify_failure=1)
        LOG.exception(f"github trend任务通知失败: {e}")

    LOG.info("[github trend定时任务执行完毕]")

def clean_report_dir_job(clean_reports):
    """
    清理报告目录任务
    """
    clean_reports.clean_all_report_dir()

def weekly_dashboard_job():
    """
    每周生成运行指标周报HTML
    """
    LOG.info("[开始生成运行指标周报]")
    try:
        filepath = generate_weekly_dashboard()
        if filepath:
            LOG.info(f"[运行指标周报已生成] {filepath}")
        else:
            LOG.warning("[运行指标周报] 本周无统计数据，跳过生成")
    except Exception as e:
        LOG.exception(f"生成运行指标周报失败: {e}")
    LOG.info("[运行指标周报任务执行完毕]")

def record_api_stats():
    """记录API统计并落盘KPI快照"""
    with api_counter_lock:
        stats = api_call_counter.copy()
        # 重置计数器
        api_call_counter["github"] = 0
        api_call_counter["hackernews"] = 0
        api_call_counter["github_trend"] = 0

    snapshot_time = datetime.now(SHANGHAI_TZ)
    total = sum(stats.values())

    LOG.info(
        f"[API统计] 日期:{snapshot_time.strftime('%Y-%m-%d')} "
        f"GitHub调用:{stats['github']} "
        f"HackerNews调用:{stats['hackernews']} "
        f"GitHub趋势调用:{stats['github_trend']} "
        f"总计:{total}"
    )

    _append_json_line(
        API_STATS_LOG,
        {
            "ts": snapshot_time.isoformat(),
            "tz": "Asia/Shanghai",
            "api_calls": {
                "github": stats["github"],
                "hackernews": stats["hackernews"],
                "github_trend": stats["github_trend"],
                "total": total
            }
        }
    )


def parse_update_execution_time(time_str):
    """解析并校验HH:MM格式的执行时间"""
    try:
        hour_str, minute_str = time_str.split(':', 1)
        hour = int(hour_str)
        minute = int(minute_str)
    except Exception as e:
        raise ValueError(f"update_execution_time格式非法: {time_str}，应为HH:MM") from e

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"update_execution_time超出范围: {time_str}")

    return hour, minute


def build_interval_start_datetime(hour, minute):
    """构建下一次GitHub任务起始时间（上海时区）"""
    now = datetime.now(SHANGHAI_TZ)
    start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if start <= now:
        start += timedelta(days=1)
    return start


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
    
    # 获取调度器实例（统一上海时区）
    scheduler = BackgroundScheduler(timezone=SHANGHAI_TZ)
    scheduler.start()
    
    # 添加任务执行事件监听（用于耗时、偏差、成功率统计）
    scheduler.add_listener(on_job_submitted, EVENT_JOB_SUBMITTED)
    scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)
    
    # 1. 清理报告目录任务（每天00:00）
    scheduler.add_job(
        clean_report_dir_job,
        'cron',
        id='clean_report_dir_job',
        replace_existing=True,
        hour=0,
        minute=0,
        args=[clean_reports],  # 传递参数
        timezone=SHANGHAI_TZ,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )

    # 2. API统计定时任务（每天00:05，避免与00:00业务任务竞争）
    scheduler.add_job(
        record_api_stats,
        'cron',
        id='record_api_stats_job',
        replace_existing=True,
        hour=0,
        minute=5,
        timezone=SHANGHAI_TZ,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )

    # 3. KPI统计落盘任务（每天00:06）
    scheduler.add_job(
        flush_kpi_stats,
        'cron',
        id='flush_kpi_stats_job',
        replace_existing=True,
        hour=0,
        minute=6,
        timezone=SHANGHAI_TZ,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300
    )

    # 3.5 运行指标周报（每周一00:10，在KPI落盘之后生成）
    scheduler.add_job(
        weekly_dashboard_job,
        'cron',
        id='weekly_dashboard_job',
        replace_existing=True,
        day_of_week='mon',
        hour=0,
        minute=10,
        timezone=SHANGHAI_TZ,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600
    )

    # 4. GitHub相关任务（每隔config.update_freq_days天，在指定时间执行）
    # github_job(github_api, subscription_manager, report_generator, notifier, config.update_freq_days)

    # 解析并校验配置中的时间和间隔天数
    hour, minute = parse_update_execution_time(config.update_execution_time)
    interval_days = int(config.update_freq_days)
    if interval_days <= 0:
        raise ValueError(f"update_freq_days必须为正整数，当前值: {config.update_freq_days}")

    github_start_date = build_interval_start_datetime(hour, minute)

    # 使用interval实现“严格每N天”语义，避免cron day步进跨月失真
    scheduler.add_job(
        github_job,
        'interval',
        id='github_job',
        replace_existing=True,
        days=interval_days,
        start_date=github_start_date,
        args=[github_api, subscription_manager, report_generator, notifier, interval_days],
        timezone=SHANGHAI_TZ,
        misfire_grace_time=600,
        max_instances=1,
        coalesce=True
    )

    # 4. HackNews小时级任务（每4小时，在第10分钟执行，避免与整点任务撞车）
    # hack_news_hours_job(hack_news_api, report_generator, notifier)
    scheduler.add_job(
        hack_news_hours_job,
        'cron',
        id='hack_news_hours_job',
        replace_existing=True,
        hour='*/4',  # 每4小时
        minute=10,
        misfire_grace_time=300,  # 允许5分钟的延迟
        args=[hack_news_api, report_generator, notifier],
        timezone=SHANGHAI_TZ,
        max_instances=1,
        coalesce=True
    )

    # 5. HackNews每日任务（每天20:30）
    # hack_news_daily_job(hack_news_api, report_generator, notifier)
    scheduler.add_job(
        hack_news_daily_job,
        'cron',
        id='hack_news_daily_job',
        replace_existing=True,
        hour=20,
        minute=30,
        args=[hack_news_api, report_generator, notifier],
        timezone=SHANGHAI_TZ,
        misfire_grace_time=600,
        max_instances=1,
        coalesce=True
    )

    # 6. GitHub趋势每日任务（每天18:00）
    # github_trend_daily_job(github_trend_api, report_generator, notifier)
    scheduler.add_job(
        github_trend_daily_job,
        'cron',
        id='github_trend_daily_job',
        replace_existing=True,
        hour=18,
        minute=0,
        args=[github_trend_api, report_generator, notifier],
        timezone=SHANGHAI_TZ,
        misfire_grace_time=600,
        max_instances=1,
        coalesce=True
    )
    
    # --------------------------
    # 主循环
    # --------------------------
    exit_code = 0
    try:
        # 只需保持主进程不退出即可
        while True:
            time.sleep(2)
    except Exception as e:
        LOG.error(f"主进程发生未捕获异常: {str(e)}")
        exit_code = 1
    finally:
        graceful_shutdown(exit_code=exit_code)
        if exit_code != 0:
            sys.exit(exit_code)
    
if __name__ == "__main__":
    main()
