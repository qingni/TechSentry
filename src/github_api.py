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
    
    def export_daily_progress(self, 
                              repo, 
                              updates, 
                              since: Optional[str] = None,
                              until: Optional[str] = None,
                              relative: Optional[str] = None) -> str:      
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
        file_path = f"{dir_path}/{sinceFormat}_{untilFormat}.md"
        
        
        # 合并默认值和用户数据
        safe_updates = {
            'issues': [],
            'pull_requests': [],
            **updates
        }
        
        try:
            # 使用w+模式打开文件，不存在则创建，存在则覆盖
            with open(file_path, 'w+', encoding='utf-8') as f:
                f.write(f"# Daily Progress for {repo}\n\n")
                f.write(f"**Report Create Date**: {Utils.format_date(datetime.now().isoformat())}\n\n")
                f.write(f"**Report Time Range**: {sinceFormat} 至 {untilFormat}\n\n")
                
                # 处理各部分内容的通用函数
                def write_section(title, items):
                    f.write(f"## {title}\n")
                    if items:
                        f.write('\n'.join(f"-  {item['title']} #{item['number']}" for item in items) + '\n\n')
                    else:
                        f.write(f"No {title.lower()} recorded.\n\n")
                
                # 依次写入各部分
                write_section("Issues", safe_updates['issues'])
                write_section("Pull Requests", safe_updates['pull_requests'])
            LOG.info(f"已导出日报至 {file_path}")
            return file_path
        
        except IOError as e:
            LOG.error(f"导出日报至 {file_path} 失败")
            raise Exception(f"Failed to write daily progress file: {str(e)}") from e


    
    
    