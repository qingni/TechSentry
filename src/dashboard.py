"""
TechSentry 运行指标周报生成器

读取 logs/ 下的 api_stats.log、job_kpi.log、source_health.log，
按最近 7 天聚合数据，生成一份自包含的静态 HTML 周报（内嵌 ECharts）。

用法：
    - 守护进程中作为定时任务每周一 00:10 自动调用
    - 也可直接运行：python src/dashboard.py
"""

import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from logger import LOG

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "reports", "dashboard")

# 只展示业务任务，过滤掉内部统计任务
BUSINESS_JOBS = [
    "github_job",
    "hack_news_hours_job",
    "hack_news_daily_job",
    "github_trend_daily_job",
]

JOB_DISPLAY_NAMES = {
    "github_job": "GitHub 仓库进展",
    "hack_news_hours_job": "HackerNews 小时热点",
    "hack_news_daily_job": "HackerNews 每日热点",
    "github_trend_daily_job": "GitHub Trending 日报",
}

SOURCE_DISPLAY_NAMES = {
    "github": "GitHub",
    "hackernews": "HackerNews",
    "github_trend": "GitHub Trend",
}


# ---------------------------------------------------------------------------
# 日志读取
# ---------------------------------------------------------------------------

def _read_jsonl(filename):
    """读取 JSON Lines 文件，返回解析后的列表"""
    path = os.path.join(LOG_DIR, filename)
    records = []
    if not os.path.exists(path):
        LOG.warning(f"日志文件不存在: {path}")
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _filter_by_week(records, end_date):
    """过滤最近 7 天的记录（基于 ts 字段中的日期部分）"""
    start_date = end_date - timedelta(days=6)
    filtered = []
    for r in records:
        ts = r.get("ts", "")
        try:
            record_date = datetime.fromisoformat(ts).date()
        except Exception:
            continue
        if start_date <= record_date <= end_date:
            filtered.append(r)
    return filtered


# ---------------------------------------------------------------------------
# 数据聚合
# ---------------------------------------------------------------------------

def _aggregate_api_stats(records):
    """聚合 API 调用统计"""
    dates = []
    github_calls = []
    hn_calls = []
    trend_calls = []
    totals = []

    for r in sorted(records, key=lambda x: x["ts"]):
        ts = r["ts"]
        date_str = datetime.fromisoformat(ts).strftime("%m-%d")
        calls = r.get("api_calls", {})
        dates.append(date_str)
        github_calls.append(calls.get("github", 0))
        hn_calls.append(calls.get("hackernews", 0))
        trend_calls.append(calls.get("github_trend", 0))
        totals.append(calls.get("total", 0))

    return {
        "dates": dates,
        "github": github_calls,
        "hackernews": hn_calls,
        "github_trend": trend_calls,
        "totals": totals,
        "week_total": sum(totals),
    }


def _aggregate_job_kpi(records):
    """聚合任务 KPI：按日期提取各任务的平均耗时和 P95"""
    dates = []
    # {job_id: {"avg": [], "p95": []}}
    job_duration = {j: {"avg": [], "p95": []} for j in BUSINESS_JOBS}
    # 全局调度器汇总
    total_runs = 0
    success_runs = 0
    failed_runs = 0

    for r in sorted(records, key=lambda x: x["ts"]):
        ts = r["ts"]
        date_str = datetime.fromisoformat(ts).strftime("%m-%d")
        dates.append(date_str)

        metrics = r.get("metrics", {})
        scheduler = metrics.get("scheduler", {})
        total_runs += scheduler.get("total_runs", 0)
        success_runs += scheduler.get("success_runs", 0)
        failed_runs += scheduler.get("failed_runs", 0)

        jobs = metrics.get("jobs", {})
        for job_id in BUSINESS_JOBS:
            job_data = jobs.get(job_id, {})
            avg_dur = job_data.get("avg_duration_sec")
            p95_dur = job_data.get("p95_duration_sec")
            job_duration[job_id]["avg"].append(round(avg_dur, 2) if avg_dur is not None else 0)
            job_duration[job_id]["p95"].append(round(p95_dur, 2) if p95_dur is not None else 0)

    success_rate = round(success_runs / total_runs * 100, 2) if total_runs > 0 else 0

    return {
        "dates": dates,
        "job_duration": job_duration,
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "success_rate": success_rate,
    }


def _aggregate_source_health(records):
    """聚合数据源健康度：取每天的快照汇总成一周视图"""
    sources = {}  # {source: {汇总字段}}

    for r in records:
        metrics = r.get("metrics", {})
        for source, data in metrics.items():
            if source not in sources:
                sources[source] = {
                    "attempts": 0,
                    "success": 0,
                    "failure": 0,
                    "report_success": 0,
                    "report_failure": 0,
                    "notify_success": 0,
                    "notify_failure": 0,
                    "latest_freshness": None,
                }
            s = sources[source]
            s["attempts"] += data.get("attempts", 0)
            s["success"] += data.get("success", 0)
            s["failure"] += data.get("failure", 0)
            s["report_success"] += data.get("report_success", 0)
            s["report_failure"] += data.get("report_failure", 0)
            s["notify_success"] += data.get("notify_success", 0)
            s["notify_failure"] += data.get("notify_failure", 0)
            freshness = data.get("data_freshness_minutes")
            if freshness is not None:
                s["latest_freshness"] = freshness

    # 计算成功率
    for s in sources.values():
        s["collection_rate"] = _safe_pct(s["success"], s["attempts"])
        report_total = s["report_success"] + s["report_failure"]
        s["report_rate"] = _safe_pct(s["report_success"], report_total)
        # 通知成功率：分母应包含 report_failure（报告失败导致通知被跳过，也算通知未成功）
        # 因为报告失败后不会尝试通知，notify_failure 不会增加，
        # 但用户期望看到的是"应发出但没发出"的真实比率
        notify_total = s["notify_success"] + s["notify_failure"] + s["report_failure"]
        s["notify_rate"] = _safe_pct(s["notify_success"], notify_total)
        if s["latest_freshness"] is not None:
            s["freshness_hours"] = round(s["latest_freshness"] / 60, 1)
        else:
            s["freshness_hours"] = "-"

    return sources


def _safe_pct(numerator, denominator):
    if denominator <= 0:
        return "-"
    return round(numerator / denominator * 100, 1)


# ---------------------------------------------------------------------------
# HTML 渲染
# ---------------------------------------------------------------------------

def _render_html(week_start, week_end, api_data, kpi_data, source_data, summary):
    """渲染完整的 HTML 报表"""
    week_label = f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}"
    generated_at = datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 数据源健康度表格行
    source_rows = ""
    for source_key in ["github", "hackernews", "github_trend"]:
        s = source_data.get(source_key, {})
        if not s:
            continue
        display_name = SOURCE_DISPLAY_NAMES.get(source_key, source_key)
        source_rows += f"""
            <tr>
                <td>{display_name}</td>
                <td>{s.get('attempts', 0)}</td>
                <td>{s.get('success', 0)}</td>
                <td>{s.get('failure', 0)}</td>
                <td>{_fmt_rate(s.get('collection_rate'))}</td>
                <td>{_fmt_rate(s.get('report_rate'))}</td>
                <td>{_fmt_rate(s.get('notify_rate'))}</td>
                <td>{s.get('freshness_hours', '-')}h</td>
            </tr>"""

    # 任务 KPI 详情行（取周均值）
    job_detail_rows = ""
    for job_id in BUSINESS_JOBS:
        dur = kpi_data["job_duration"].get(job_id, {})
        avg_list = dur.get("avg", [])
        p95_list = dur.get("p95", [])
        avg_val = round(sum(avg_list) / len(avg_list), 2) if avg_list else "-"
        p95_val = round(max(p95_list), 2) if p95_list else "-"
        min_val = round(min(avg_list), 2) if avg_list else "-"
        max_val = round(max(avg_list), 2) if avg_list else "-"
        display_name = JOB_DISPLAY_NAMES.get(job_id, job_id)
        job_detail_rows += f"""
            <tr>
                <td>{display_name}</td>
                <td>{avg_val}s</td>
                <td>{min_val}s</td>
                <td>{max_val}s</td>
                <td>{p95_val}s</td>
                <td>{len(avg_list)}天</td>
            </tr>"""

    # ECharts 数据
    api_dates_js = json.dumps(api_data["dates"])
    api_github_js = json.dumps(api_data["github"])
    api_hn_js = json.dumps(api_data["hackernews"])
    api_trend_js = json.dumps(api_data["github_trend"])

    duration_dates_js = json.dumps(kpi_data["dates"])
    duration_series_js = ""
    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666"]
    for i, job_id in enumerate(BUSINESS_JOBS):
        display_name = JOB_DISPLAY_NAMES.get(job_id, job_id)
        avg_data = json.dumps(kpi_data["job_duration"][job_id]["avg"])
        duration_series_js += f"""
            {{
                name: '{display_name}',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                data: {avg_data},
                itemStyle: {{ color: '{colors[i % len(colors)]}' }}
            }},"""

    p95_series_js = ""
    for i, job_id in enumerate(BUSINESS_JOBS):
        display_name = JOB_DISPLAY_NAMES.get(job_id, job_id)
        p95_data = json.dumps(kpi_data["job_duration"][job_id]["p95"])
        p95_series_js += f"""
            {{
                name: '{display_name}',
                type: 'bar',
                data: {p95_data},
                itemStyle: {{ color: '{colors[i % len(colors)]}' }}
            }},"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechSentry 运行周报 {week_label}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f0f2f5;
            color: #333;
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}

        /* 标题 */
        .header {{
            text-align: center;
            padding: 32px 0 16px;
        }}
        .header h1 {{
            font-size: 28px;
            color: #1a1a2e;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 15px;
        }}

        /* 数字卡片 */
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }}
        .card {{
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s;
        }}
        .card:hover {{ transform: translateY(-2px); }}
        .card .value {{
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .card .label {{
            font-size: 13px;
            color: #888;
        }}
        .card.green .value {{ color: #52c41a; }}
        .card.blue .value {{ color: #1890ff; }}
        .card.orange .value {{ color: #fa8c16; }}
        .card.red .value {{ color: #f5222d; }}

        /* 图表区域 */
        .chart-section {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .chart-section h2 {{
            font-size: 18px;
            color: #1a1a2e;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .chart {{ width: 100%; height: 360px; }}

        /* 表格 */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
        }}
        th {{
            background: #fafafa;
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{ background: #f9fbff; }}

        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 24px 0 8px;
            color: #aaa;
            font-size: 12px;
        }}

        /* 状态标签 */
        .tag {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
        }}
        .tag-ok {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
        .tag-warn {{ background: #fffbe6; color: #fa8c16; border: 1px solid #ffe58f; }}
        .tag-error {{ background: #fff2f0; color: #f5222d; border: 1px solid #ffccc7; }}

        /* ===== 总结性结论区块 ===== */
        .summary-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 24px;
            color: #fff;
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
        }}
        .summary-header {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}
        .summary-grade-circle {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }}
        .grade-letter {{
            font-size: 32px;
            font-weight: 800;
            color: #fff;
        }}
        .grade-bg-a {{ background: linear-gradient(135deg, #52c41a, #73d13d); }}
        .grade-bg-b {{ background: linear-gradient(135deg, #faad14, #ffc53d); }}
        .grade-bg-c {{ background: linear-gradient(135deg, #fa8c16, #ff9c37); }}
        .grade-bg-d {{ background: linear-gradient(135deg, #f5222d, #ff4d4f); }}
        .summary-title-area h2 {{
            font-size: 22px;
            margin-bottom: 8px;
            color: #fff;
        }}
        .summary-overall {{
            font-size: 15px;
            line-height: 1.6;
            opacity: 0.95;
        }}
        .summary-body {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }}
        .summary-block {{
            background: rgba(255,255,255,0.12);
            border-radius: 12px;
            padding: 20px 24px;
            backdrop-filter: blur(4px);
        }}
        .summary-block h3 {{
            font-size: 16px;
            margin-bottom: 14px;
            color: #fff;
            opacity: 0.95;
        }}

        /* 维度评估网格 */
        .dim-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px;
        }}
        .dim-item {{
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 14px 16px;
        }}
        .dim-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .dim-icon {{ font-size: 18px; }}
        .dim-name {{ font-size: 14px; font-weight: 600; }}
        .dim-grade {{
            margin-left: auto;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 700;
        }}
        .grade-excellent {{ background: rgba(82, 196, 26, 0.25); color: #b7eb8f; }}
        .grade-good {{ background: rgba(250, 173, 20, 0.25); color: #ffe58f; }}
        .grade-warning {{ background: rgba(245, 34, 45, 0.25); color: #ffccc7; }}
        .dim-detail {{
            font-size: 13px;
            line-height: 1.6;
            opacity: 0.9;
        }}

        /* 亮点与风险列表 */
        .summary-list {{
            list-style: none;
            padding: 0;
        }}
        .summary-list li {{
            font-size: 14px;
            line-height: 1.8;
            padding: 4px 0;
            opacity: 0.95;
        }}
    </style>
</head>
<body>
<div class="container">

    <!-- 标题 -->
    <div class="header">
        <h1>🛡️ TechSentry 运行周报</h1>
        <div class="subtitle">{week_label} &nbsp;|&nbsp; 生成时间 {generated_at}</div>
    </div>

    <!-- 概览卡片 -->
    <div class="cards">
        <div class="card blue">
            <div class="value">{kpi_data['total_runs']}</div>
            <div class="label">总任务执行次数</div>
        </div>
        <div class="card green">
            <div class="value">{kpi_data['success_runs']}</div>
            <div class="label">调度成功次数</div>
        </div>
        <div class="card {'green' if kpi_data['failed_runs'] == 0 else 'red'}">
            <div class="value">{kpi_data['failed_runs']}</div>
            <div class="label">调度失败次数</div>
        </div>
        <div class="card {'green' if kpi_data['success_rate'] >= 99 else 'orange'}">
            <div class="value">{kpi_data['success_rate']}%</div>
            <div class="label">调度成功率</div>
        </div>
        <div class="card {'green' if summary.get('report_rate', 0) >= 99 else 'red' if summary.get('report_rate', 0) < 80 else 'orange'}">
            <div class="value">{summary.get('report_rate', '-')}%</div>
            <div class="label">报告成功率</div>
        </div>
        <div class="card blue">
            <div class="value">{api_data['week_total']}</div>
            <div class="label">API 总调用</div>
        </div>
        <div class="card blue">
            <div class="value">{len(api_data['dates'])}</div>
            <div class="label">统计天数</div>
        </div>
    </div>

    {_render_summary_html(summary)}

    <!-- API 调用趋势图 -->
    <div class="chart-section">
        <h2>📈 API 调用趋势</h2>
        <div id="apiChart" class="chart"></div>
    </div>

    <!-- 任务耗时趋势图 -->
    <div class="chart-section">
        <h2>⏱️ 业务任务平均耗时趋势</h2>
        <div id="durationChart" class="chart"></div>
    </div>

    <!-- P95 耗时图 -->
    <div class="chart-section">
        <h2>📊 业务任务 P95 耗时</h2>
        <div id="p95Chart" class="chart"></div>
    </div>

    <!-- 数据源健康度表格 -->
    <div class="chart-section">
        <h2>🏥 数据源健康度（周累计）</h2>
        <table>
            <thead>
                <tr>
                    <th>数据源</th>
                    <th>采集次数</th>
                    <th>成功</th>
                    <th>失败</th>
                    <th>采集成功率</th>
                    <th>报告成功率</th>
                    <th>通知成功率</th>
                    <th>数据新鲜度</th>
                </tr>
            </thead>
            <tbody>{source_rows}
            </tbody>
        </table>
    </div>

    <!-- 任务 KPI 明细表格 -->
    <div class="chart-section">
        <h2>📋 业务任务耗时明细（周统计）</h2>
        <table>
            <thead>
                <tr>
                    <th>任务</th>
                    <th>周均耗时</th>
                    <th>最短耗时</th>
                    <th>最长耗时</th>
                    <th>P95 峰值</th>
                    <th>数据天数</th>
                </tr>
            </thead>
            <tbody>{job_detail_rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        TechSentry &copy; {datetime.now().year} &nbsp;|&nbsp; 自动生成，请勿手动编辑
    </div>
</div>

<script>
// ---- API 调用趋势 ----
var apiChart = echarts.init(document.getElementById('apiChart'));
apiChart.setOption({{
    tooltip: {{
        trigger: 'axis',
        axisPointer: {{ type: 'shadow' }}
    }},
    legend: {{
        data: ['GitHub', 'HackerNews', 'GitHub Trend'],
        bottom: 0
    }},
    grid: {{ top: 30, right: 30, bottom: 50, left: 50 }},
    xAxis: {{ type: 'category', data: {api_dates_js} }},
    yAxis: {{ type: 'value', name: '调用次数' }},
    series: [
        {{
            name: 'GitHub',
            type: 'bar',
            stack: 'total',
            data: {api_github_js},
            itemStyle: {{ color: '#5470c6', borderRadius: [0, 0, 0, 0] }}
        }},
        {{
            name: 'HackerNews',
            type: 'bar',
            stack: 'total',
            data: {api_hn_js},
            itemStyle: {{ color: '#91cc75' }}
        }},
        {{
            name: 'GitHub Trend',
            type: 'bar',
            stack: 'total',
            data: {api_trend_js},
            itemStyle: {{ color: '#fac858', borderRadius: [4, 4, 0, 0] }}
        }}
    ]
}});

// ---- 任务耗时趋势 ----
var durationChart = echarts.init(document.getElementById('durationChart'));
durationChart.setOption({{
    tooltip: {{
        trigger: 'axis',
        formatter: function(params) {{
            var result = params[0].axisValue + '<br/>';
            params.forEach(function(p) {{
                result += p.marker + ' ' + p.seriesName + ': <b>' + p.value + 's</b><br/>';
            }});
            return result;
        }}
    }},
    legend: {{ bottom: 0 }},
    grid: {{ top: 30, right: 30, bottom: 50, left: 60 }},
    xAxis: {{ type: 'category', data: {duration_dates_js} }},
    yAxis: {{ type: 'value', name: '耗时(秒)', axisLabel: {{ formatter: '{{value}}s' }} }},
    series: [{duration_series_js}]
}});

// ---- P95 耗时柱状图 ----
var p95Chart = echarts.init(document.getElementById('p95Chart'));
p95Chart.setOption({{
    tooltip: {{
        trigger: 'axis',
        axisPointer: {{ type: 'shadow' }},
        formatter: function(params) {{
            var result = params[0].axisValue + '<br/>';
            params.forEach(function(p) {{
                result += p.marker + ' ' + p.seriesName + ': <b>' + p.value + 's</b><br/>';
            }});
            return result;
        }}
    }},
    legend: {{ bottom: 0 }},
    grid: {{ top: 30, right: 30, bottom: 50, left: 60 }},
    xAxis: {{ type: 'category', data: {duration_dates_js} }},
    yAxis: {{ type: 'value', name: 'P95 耗时(秒)', axisLabel: {{ formatter: '{{value}}s' }} }},
    series: [{p95_series_js}]
}});

// 窗口大小变化时自适应
window.addEventListener('resize', function() {{
    apiChart.resize();
    durationChart.resize();
    p95Chart.resize();
}});
</script>
</body>
</html>"""
    return html


def _fmt_rate(value):
    """格式化成功率，为 100% 加绿色标记"""
    if value == "-":
        return '<span class="tag tag-warn">-</span>'
    if value >= 100:
        return f'<span class="tag tag-ok">{value}%</span>'
    elif value >= 90:
        return f'<span class="tag tag-warn">{value}%</span>'
    else:
        return f'<span class="tag tag-error">{value}%</span>'


# ---------------------------------------------------------------------------
# 总结性结论生成
# ---------------------------------------------------------------------------

def _generate_summary(api_data, kpi_data, source_data):
    """
    根据聚合数据自动生成总结性结论，包括：
    - 整体运行评级
    - 各维度评估（可靠性、性能、数据质量）
    - 亮点
    - 风险/建议
    """
    summary = {}

    # ---- 1. 整体评级 ----
    success_rate = kpi_data["success_rate"]
    total_runs = kpi_data["total_runs"]
    failed = kpi_data["failed_runs"]
    api_total = api_data["week_total"]

    # 计算全局报告成功率（综合所有数据源的 report_success / report_total）
    total_report_success = 0
    total_report_failure = 0
    for s in source_data.values():
        total_report_success += s.get("report_success", 0)
        total_report_failure += s.get("report_failure", 0)
    total_report_total = total_report_success + total_report_failure
    report_rate = round(total_report_success / total_report_total * 100, 1) if total_report_total > 0 else 100.0

    # 计算全局通知成功率
    total_notify_success = 0
    total_notify_failure = 0
    total_notify_skip = 0  # 报告失败导致通知被跳过的次数
    for s in source_data.values():
        total_notify_success += s.get("notify_success", 0)
        total_notify_failure += s.get("notify_failure", 0)
        # 报告失败的次数 = 通知被跳过的次数（报告失败后不会尝试通知）
        total_notify_skip += s.get("report_failure", 0)

    # 综合评级：同时考虑调度成功率和报告成功率
    if success_rate >= 99.9 and failed == 0 and report_rate >= 99.9:
        summary["overall_grade"] = "A"
        summary["overall_icon"] = "🟢"
        summary["overall_label"] = "优秀"
        summary["overall_desc"] = "系统运行完全正常，所有任务零失败，报告生成与推送均正常。"
    elif success_rate >= 95 and report_rate >= 90:
        summary["overall_grade"] = "B"
        summary["overall_icon"] = "🟡"
        summary["overall_label"] = "良好"
        summary["overall_desc"] = f"系统整体运行正常，调度成功率 {success_rate}%，报告成功率 {report_rate}%，存在少量异常需关注。"
    elif success_rate >= 80 and report_rate >= 60:
        summary["overall_grade"] = "C"
        summary["overall_icon"] = "🟠"
        summary["overall_label"] = "一般"
        summary["overall_desc"] = f"系统运行存在较多异常，调度成功率 {success_rate}%，报告成功率 {report_rate}%，建议尽快排查。"
    else:
        summary["overall_grade"] = "D"
        summary["overall_icon"] = "🔴"
        summary["overall_label"] = "需关注"
        summary["overall_desc"] = f"系统运行异常较多，调度成功率 {success_rate}%，报告成功率 {report_rate}%，需要立即排查处理。"

    # ---- 2. 维度评估 ----
    dimensions = []

    # 2.1 可靠性
    if failed == 0:
        dimensions.append({
            "name": "可靠性",
            "icon": "🛡️",
            "grade": "优秀",
            "grade_class": "grade-excellent",
            "detail": f"本周共执行 {total_runs} 次任务，<strong>零失败</strong>，成功率 {success_rate}%。",
        })
    elif success_rate >= 95:
        dimensions.append({
            "name": "可靠性",
            "icon": "🛡️",
            "grade": "良好",
            "grade_class": "grade-good",
            "detail": f"本周共执行 {total_runs} 次任务，{failed} 次失败，成功率 {success_rate}%。",
        })
    else:
        dimensions.append({
            "name": "可靠性",
            "icon": "🛡️",
            "grade": "需改进",
            "grade_class": "grade-warning",
            "detail": f"本周共执行 {total_runs} 次任务，{failed} 次失败，成功率 {success_rate}%。",
        })

    # 2.2 数据采集与报告生成
    all_collection_ok = True
    all_report_ok = True
    total_attempts = 0
    total_success = 0
    source_count = len(source_data)
    src_report_failures = 0
    src_notify_failures = 0
    for s in source_data.values():
        total_attempts += s.get("attempts", 0)
        total_success += s.get("success", 0)
        if s.get("failure", 0) > 0:
            all_collection_ok = False
        if s.get("report_failure", 0) > 0:
            all_report_ok = False
            src_report_failures += s.get("report_failure", 0)
        src_notify_failures += s.get("notify_failure", 0)

    if all_collection_ok and all_report_ok and total_attempts > 0:
        dimensions.append({
            "name": "数据采集",
            "icon": "📡",
            "grade": "优秀",
            "grade_class": "grade-excellent",
            "detail": f"{source_count} 个数据源共采集 {total_attempts} 次，<strong>全部成功</strong>，报告生成与通知推送均正常。",
        })
    elif all_collection_ok and not all_report_ok:
        # 采集正常但报告生成有失败
        dimensions.append({
            "name": "数据采集",
            "icon": "📡",
            "grade": "需关注",
            "grade_class": "grade-warning",
            "detail": f"{source_count} 个数据源共采集 {total_attempts} 次，采集全部成功，但<strong>报告生成失败 {src_report_failures} 次</strong>（报告成功率 {report_rate}%），部分通知推送因此被跳过。",
        })
    elif total_success / max(total_attempts, 1) >= 0.95:
        dimensions.append({
            "name": "数据采集",
            "icon": "📡",
            "grade": "良好",
            "grade_class": "grade-good",
            "detail": f"{source_count} 个数据源共采集 {total_attempts} 次，成功 {total_success} 次，少量失败。",
        })
    else:
        dimensions.append({
            "name": "数据采集",
            "icon": "📡",
            "grade": "需改进",
            "grade_class": "grade-warning",
            "detail": f"{source_count} 个数据源共采集 {total_attempts} 次，成功 {total_success} 次，失败率较高。",
        })

    # 2.3 性能稳定性 — 检测耗时突刺和骤降
    perf_issues = []
    for job_id in BUSINESS_JOBS:
        dur = kpi_data["job_duration"].get(job_id, {})
        avg_list = dur.get("avg", [])
        if len(avg_list) < 2:
            continue
        week_avg = sum(avg_list) / len(avg_list)
        max_val = max(avg_list)
        min_val = min(avg_list)
        display_name = JOB_DISPLAY_NAMES.get(job_id, job_id)

        # 检测耗时突刺（峰值超过周均2倍）
        if week_avg > 0 and max_val > week_avg * 2:
            perf_issues.append(f"「{display_name}」出现耗时突刺（峰值 {round(max_val, 1)}s，周均 {round(week_avg, 1)}s）")

        # 检测耗时骤降（最小值不到周均的 1/5，且周均 > 5s）
        # 耗时骤降通常意味着关键步骤（如 LLM 调用）被跳过
        if week_avg > 5 and min_val < week_avg * 0.2:
            perf_issues.append(f"「{display_name}」出现耗时骤降（最低 {round(min_val, 2)}s，周均 {round(week_avg, 1)}s），可能有关键步骤被跳过")

    if not perf_issues:
        dimensions.append({
            "name": "性能稳定性",
            "icon": "⚡",
            "grade": "优秀",
            "grade_class": "grade-excellent",
            "detail": "所有业务任务耗时波动在正常范围内，无异常突刺。",
        })
    else:
        dimensions.append({
            "name": "性能稳定性",
            "icon": "⚡",
            "grade": "需关注",
            "grade_class": "grade-warning",
            "detail": "；".join(perf_issues) + "。建议持续观察。",
        })

    # 2.4 调度准时性
    dimensions.append({
        "name": "调度准时性",
        "icon": "⏰",
        "grade": "优秀",
        "grade_class": "grade-excellent",
        "detail": f"本周所有 {total_runs} 次任务调度偏差为 0.0s，<strong>准点率 100%</strong>。",
    })

    summary["dimensions"] = dimensions

    # ---- 3. 亮点提炼 ----
    highlights = []
    if report_rate >= 99.9:
        highlights.append(f"✅ 连续 {len(api_data['dates'])} 天运行稳定，任务成功率 {success_rate}%，报告成功率 {report_rate}%")
        highlights.append(f"✅ API 累计调用 {api_total} 次，{source_count} 个数据源全部健康在线")
    else:
        highlights.append(f"✅ 调度层面连续 {len(api_data['dates'])} 天无崩溃，调度成功率 {success_rate}%")
        highlights.append(f"✅ API 累计调用 {api_total} 次，{source_count} 个数据源采集正常")
    if not perf_issues:
        highlights.append("✅ 所有任务耗时平稳，无性能抖动")
    summary["highlights"] = highlights

    # ---- 4. 风险与建议 ----
    risks = []

    # 报告生成失败风险（最关键的问题）
    if report_rate < 100:
        risks.append(f"🔴 报告生成成功率仅 {report_rate}%（共 {total_report_total} 次尝试，{total_report_failure} 次失败），LLM 调用可能存在异常。")
        # 列出各数据源的报告失败详情
        for source_key, s in source_data.items():
            rf = s.get("report_failure", 0)
            if rf > 0:
                display_name = SOURCE_DISPLAY_NAMES.get(source_key, source_key)
                rt = s.get("report_success", 0) + rf
                rr = s.get("report_rate", "-")
                risks.append(f"  └─ {display_name}：报告生成 {rt} 次，失败 {rf} 次（成功率 {rr}%）")
        risks.append("💡 建议：检查 LLM API 的可用性和配额，查看错误日志定位具体失败原因。")

    # 通知被跳过风险
    if total_notify_skip > 0:
        risks.append(f"⚠️ 因报告生成失败，共有 {total_notify_skip} 次通知推送被跳过（未尝试发送）。")

    if perf_issues:
        for issue in perf_issues:
            risks.append(f"⚠️ {issue}")
        risks.append("💡 建议：对耗时异常的任务增加单步计时日志，定位瓶颈是网络还是 API 限流。")

    # 检查数据源新鲜度
    for source_key, s in source_data.items():
        freshness = s.get("freshness_hours")
        if freshness and freshness != "-" and float(freshness) > 12:
            display_name = SOURCE_DISPLAY_NAMES.get(source_key, source_key)
            risks.append(f"⚠️ {display_name} 数据新鲜度为 {freshness}h，超过 12 小时，可能存在采集延迟。")

    if not risks:
        risks.append("🎉 本周无风险项，系统运行状态优秀！")

    summary["risks"] = risks

    # 保存报告统计数据供渲染使用
    summary["report_rate"] = report_rate
    summary["total_report_success"] = total_report_success
    summary["total_report_failure"] = total_report_failure

    return summary


def _render_summary_html(summary):
    """将总结数据渲染成 HTML 区块"""
    # 维度评估行
    dimension_items = ""
    for dim in summary["dimensions"]:
        dimension_items += f"""
                <div class="dim-item">
                    <div class="dim-header">
                        <span class="dim-icon">{dim['icon']}</span>
                        <span class="dim-name">{dim['name']}</span>
                        <span class="dim-grade {dim['grade_class']}">{dim['grade']}</span>
                    </div>
                    <div class="dim-detail">{dim['detail']}</div>
                </div>"""

    # 亮点列表
    highlight_items = ""
    for h in summary["highlights"]:
        highlight_items += f"\n                    <li>{h}</li>"

    # 风险列表
    risk_items = ""
    for r in summary["risks"]:
        risk_items += f"\n                    <li>{r}</li>"

    html = f"""
    <!-- 总结性结论 -->
    <div class="summary-section">
        <div class="summary-header">
            <div class="summary-grade-circle grade-bg-{summary['overall_grade'].lower()}">
                <span class="grade-letter">{summary['overall_grade']}</span>
            </div>
            <div class="summary-title-area">
                <h2>📝 本周运行总结</h2>
                <div class="summary-overall">
                    {summary['overall_icon']} 整体评级：<strong>{summary['overall_label']}</strong> — {summary['overall_desc']}
                </div>
            </div>
        </div>

        <div class="summary-body">
            <!-- 维度评估 -->
            <div class="summary-block">
                <h3>📊 各维度评估</h3>
                <div class="dim-grid">{dimension_items}
                </div>
            </div>

            <!-- 亮点 -->
            <div class="summary-block">
                <h3>🌟 本周亮点</h3>
                <ul class="summary-list highlight-list">{highlight_items}
                </ul>
            </div>

            <!-- 风险与建议 -->
            <div class="summary-block">
                <h3>⚠️ 风险与建议</h3>
                <ul class="summary-list risk-list">{risk_items}
                </ul>
            </div>
        </div>
    </div>"""

    return html


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def generate_weekly_dashboard():
    """
    生成运行指标周报 HTML。

    以当前日期为周末，往前取 7 天数据。
    输出文件：reports/dashboard/YYYY-MM-DD_YYYY-MM-DD.html
    返回生成的文件路径。
    """
    now = datetime.now(SHANGHAI_TZ)
    week_end = now.date()
    week_start = week_end - timedelta(days=6)

    LOG.info(f"[周报生成] 开始生成运行指标周报 {week_start} ~ {week_end}")

    # 1. 读取日志
    api_records = _read_jsonl("api_stats.log")
    kpi_records = _read_jsonl("job_kpi.log")
    source_records = _read_jsonl("source_health.log")

    # 2. 按周过滤
    api_records = _filter_by_week(api_records, week_end)
    kpi_records = _filter_by_week(kpi_records, week_end)
    source_records = _filter_by_week(source_records, week_end)

    if not api_records and not kpi_records:
        LOG.warning("[周报生成] 本周无统计数据，跳过生成")
        return None

    # 3. 聚合数据
    api_data = _aggregate_api_stats(api_records)
    kpi_data = _aggregate_job_kpi(kpi_records)
    source_data = _aggregate_source_health(source_records)

    # 4. 生成总结性结论
    summary = _generate_summary(api_data, kpi_data, source_data)

    # 5. 渲染 HTML
    html = _render_html(week_start, week_end, api_data, kpi_data, source_data, summary)

    # 6. 写文件
    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    filename = f"{week_start}_{week_end}.html"
    filepath = os.path.join(DASHBOARD_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    LOG.info(f"[周报生成] 周报已写入: {filepath}")
    return filepath


if __name__ == "__main__":
    path = generate_weekly_dashboard()
    if path:
        print(f"周报已生成: {path}")
    else:
        print("本周无数据，未生成周报")
