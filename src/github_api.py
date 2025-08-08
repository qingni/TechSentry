import requests
import datetime

class GitHubAPI:
    def __init__(self, token):
        self.headers = {"Authorization": f"token {token}"}
        self.base_url = "https://api.github.com"

    def fetch_updates(self, repo):
        updates = {
            # 'commits': self.fetch_commits(repo),
            'pull_requests': self.fetch_pull_requests(repo),
            'issues': self.fetch_issues(repo)
        }
        return updates
    
    def fetch_pull_requests(self, repo):
        url = f"{self.base_url}/repos/{repo}/pulls"
        response = requests.get(url, headers=self.headers)
        # 标准异常处理方式
        response.raise_for_status()
        return response.json()
    
    def fetch_issues(self, repo):
        url = f"{self.base_url}/repos/{repo}/issues"
        response = requests.get(url, headers=self.headers)
        # 标准异常处理方式
        response.raise_for_status()
        return response.json()
    
    def fetch_commits(self, repo):
        url = f"{self.base_url}/repos/{repo}/commits"
        response = requests.get(url, headers=self.headers)
        # 标准异常处理方式
        response.raise_for_status()
        return response.json()

    def export_repo_daily_progress(self, repo):
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        issues = self.fetch_issues(repo)
        pull_requests = self.fetch_pull_requests(repo)
        filename = f'daily_progress/{repo.replace("/", "_")}_{date_str}.md'
        with open(filename, 'w') as f:
            f.write(f"# {repo} Daily Progress - {date_str}\n\n")
            f.write("## Issues\n")
            for issue in issues:
                f.write(f"- {issue['title']} #{issue['number']}\n")
            f.write("\n## Pull Requests\n")
            for pr in pull_requests:
                f.write(f"- {pr['title']} #{pr['number']}\n")

        print(f"Exported daily progress to {filename}")

        return filename   