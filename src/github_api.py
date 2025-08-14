import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import os
from utils import Utils
from logger import LOG
class GitHubAPI:
    """增强版GitHub API客户端，支持相对时间范围和状态筛选"""

    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.github.com"

    def fetch_updates(self, repo: str, since: Optional[str] = None, 
                     until: Optional[str] = None, relative: Optional[str] = None) -> Dict:
        """
        获取仓库更新信息
        
        Args:
            repo: 仓库名称 (格式: owner/repo)
            since: 开始时间 (ISO 8601格式: YYYY-MM-DDTHH:MM:SSZ)
            until: 结束时间 (ISO 8601格式: YYYY-MM-DDTHH:MM:SSZ)
            relative: 相对时间范围 ('24hours', '3days', '1week', '1month')
        """
        # 处理时间参数
        since, until = Utils._process_time_params(since, until, relative)
        
        LOG.info(f"fetch_updates----", repo, since, until)
        updates = {
            'pull_requests': self.fetch_pull_requests(repo, since, until),
            'issues': self.fetch_issues(repo, since, until)
        }
        return updates

    
    def fetch_pull_requests(self, repo: str, since: Optional[str] = None, 
                          until: Optional[str] = None) -> List[Dict]:
        """
        获取指定时间范围内的Pull Requests
        """
        url = f"{self.base_url}/repos/{repo}/pulls"
        params = {
            'state': 'closed',  # 获取已关闭状态的PR
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100  # 每页最多100条
        }
        
        all_prs = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            prs = response.json()
            if not prs:
                break
                
            # 过滤时间范围内的PR
            filtered_prs = self._filter_by_time(prs, since, until, 'updated_at')
            all_prs.extend(filtered_prs)
            # 如果当前页最后一条记录已经超出时间范围，停止翻页
            if prs and since and prs[-1]['updated_at'] < since:
                break
                
            page += 1
            
        return all_prs
    
    def fetch_issues(self, repo: str, since: Optional[str] = None, 
                    until: Optional[str] = None) -> List[Dict]:
        """
        获取指定时间范围内的Issues（不包含PR）
        """
        url = f"{self.base_url}/repos/{repo}/issues"
        params = {
            'state': 'closed',  # 获取已关闭状态的issue
            'sort': 'updated',
            'direction': 'desc',
            'per_page': 100
        }
        
        # GitHub API支持since参数
        if since:
            params['since'] = since
            
        all_issues = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            issues = response.json()
            if not issues:
                break
                
            # 过滤掉PR（GitHub API中PR也被当作issue返回）
            issues = [issue for issue in issues if 'pull_request' not in issue]
            
            # 如果指定了until，需要手动过滤
            if until:
                issues = self._filter_by_time(issues, None, until, 'updated_at')
                
            all_issues.extend(issues)
            
            # 如果当前页最后一条记录已经超出时间范围，停止翻页
            if issues and until and issues[-1]['updated_at'] > until:
                break
                
            page += 1
            
        return all_issues
    
    def _filter_by_time(self, items: List[Dict], since: Optional[str], 
                       until: Optional[str], time_field: str) -> List[Dict]:
        """根据时间范围过滤数据"""
        filtered = []
        
        for item in items:
            item_time = item.get(time_field)
            if not item_time:
                continue
                
            # 检查是否在时间范围内
            if since and item_time < since:
                continue
            if until and item_time > until:
                continue
                
            filtered.append(item)
            
        return filtered
    
    def export_repo_daily_progress(self, 
                              repo: str,
                              since: Optional[str] = None,
                              until: Optional[str] = None,
                              relative: Optional[str] = None) -> str:
        """导出指定仓库的进度报告，相对时间也采用since_until格式命名"""

        # 解析时间范围，获取标准化的since和until
        since, until = Utils._process_time_params(since, until, relative)
        # 处理时间范围
        sinceFormat = Utils.format_date(since)
        untilFormat = Utils.format_date(until)

        # 解析仓库所有者和名称
        owner, repo_name = Utils._parse_repo(repo)
        
        # 创建存储目录 (daily_progress/owner/repo/)
        dir_path = f"daily_progress/{owner}/{repo_name}"
        os.makedirs(dir_path, exist_ok=True)  # 确保目录存在
        
        # 生成文件名 (统一采用since_until.md格式)
        filename = f"{dir_path}/{sinceFormat}_{untilFormat}.md"
        
        # 获取数据
        issues = self.fetch_issues(repo, since=since, until=until)
        pull_requests = self.fetch_pull_requests(repo, since=since, until=until)
        
        # 写入Markdown内容
        with open(filename, 'w', encoding='utf-8') as f:
            # 确定时间范围描述（保留相对时间的友好名称）
            if relative:
                time_desc = f"{Utils._get_relative_time_desc(relative)} ({sinceFormat} 至 {untilFormat})"
            else:
                time_desc = f"{sinceFormat} 至 {untilFormat}"
                
            # 标题和元信息
            f.write(f"# {owner}/{repo_name} 进度报告\n\n")
            f.write(f"**生成时间**: {Utils.format_date(datetime.now().isoformat())}\n")
            f.write(f"**时间范围**: {time_desc}\n\n")
            
            # Issues部分（仅保留标题和编号）
            f.write("## Issues\n")
            f.write(f"共 {len(issues)} 个符合条件的Issues\n")
            for issue in issues[:20]:
                f.write(f"- #{issue['number']}: {issue['title']}\n")
            
            # Pull Requests部分（仅保留标题和编号）
            f.write("\n## Pull Requests\n")
            f.write(f"共 {len(pull_requests)} 个符合条件的PRs\n")
            for pr in pull_requests[:20]:
                f.write(f"- #{pr['number']}: {pr['title']}\n")

        LOG.info(f"已导出进度报告至 {filename}")
        return filename

    
    
    