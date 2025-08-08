import requests

class GitHubAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"

    def get_repo_updates(self, repo):
        headers = {"Authorization": f"token {self.token}"}
        url = f"{self.base_url}/repos/{repo}/events"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch updates for {repo}")
