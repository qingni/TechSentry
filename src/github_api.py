import requests
class GitHubAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"

    def fetch_updates(self, subscriptions):
        headers = {"Authorization": f"token {self.token}"}
        
        updates = {}
        for repo in subscriptions:
            url = f"{self.base_url}/repos/{repo}/releases/latest"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                updates[repo] = response.json()
            else:
                raise Exception(f"Failed to fetch latest release for {repo}")          
        return updates
