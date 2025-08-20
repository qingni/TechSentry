import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

class GithubTrendAPI:
  def __init__(self):
    self.headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
      "Referer": "https://github.com/"
    }
    self.url = "https://github.com/trending?since=daily"
    
  def get_github_trending(self) -> list[dict]:
      

      try:
          response = requests.get(self.url, headers=self.headers, timeout=10)
          response.raise_for_status()
          soup = BeautifulSoup(response.text, "html.parser")

          repo_containers = soup.find_all("article", class_="Box-row")
          if not repo_containers:
              print("未找到仓库列表，可能页面结构已更新或请求被拦截")
              return []

          repo_data = []
          for repo in repo_containers:
              repo_name_elem = repo.find("h2", class_="h3 lh-condensed")
              repo_name = repo_name_elem.get_text(strip=True).replace(" ", "").replace("\n", "") if repo_name_elem else "未知名称"

              # 调整：通过更精确的选择器获取仓库说明
              repo_desc_elem = repo.find("p", class_="col-9 color-fg-muted my-1 pr-4")
              repo_desc = repo_desc_elem.get_text(strip=True) if repo_desc_elem else "无说明"

              lang_elem = repo.find("span", class_="d-inline-block ml-0 mr-3")
              repo_lang = lang_elem.get_text(strip=True) if lang_elem else "无"

              stats_elem = repo.find("div", class_="f6 color-fg-muted mt-2")
              star_count = "0"
              fork_count = "0"

              if stats_elem:
                  star_elem = stats_elem.find("a", href=lambda href: href and "/stargazers" in href)
                  if star_elem:
                      star_count = star_elem.get_text(strip=True).replace(",", "")

                  fork_elem = stats_elem.find("a", href=lambda href: href and "/forks" in href)
                  if fork_elem:
                      fork_count = fork_elem.get_text(strip=True).replace(",", "")

              repo_data.append({
                  "repo_name": repo_name,
                  "repo_desc": repo_desc,
                  "star": int(star_count) if star_count.isdigit() else 0,
                  "fork": int(fork_count) if fork_count.isdigit() else 0,
                  "language": repo_lang
              })

          return repo_data

      except requests.exceptions.RequestException as e:
          print(f"请求失败：{str(e)}")
          return []

  def export_daily_github_trend(self, repos: list[dict], directory: str = "github_trend"):
      """
      将仓库列表导出到Markdown文件
      :param repos: 仓库列表数据
      :param directory: 输出目录
      """
      # 创建目录
      if not os.path.exists(directory):
          os.makedirs(directory)
      
      # 生成文件名
      today = datetime.now().strftime("%Y-%m-%d")
      file_path = os.path.join(directory, f"{today}.md")
      
      # 写入Markdown内容
      with open(file_path, "w", encoding="utf-8") as f:
          f.write(f"# GitHub每日趋势仓库 {today}\n\n")
          
          for repo in repos:
              # 以仓库名作为标题
              f.write(f"## [{repo['repo_name']}](https://github.com/{repo['repo_name']})\n\n")
              # 其他信息作为内容
              f.write(f"- **描述**: {repo['repo_desc']}\n")
              f.write(f"- **Star数**: {repo['star']}\n")
              f.write(f"- **Fork数**: {repo['fork']}\n")
              f.write(f"- **语言**: {repo['language']}\n\n")
      
      print(f"已导出到文件: {file_path}")

if __name__ == "__main__":
    githubTrendAPI = GithubTrendAPI()
    print("开始爬取GitHub每日趋势仓库...")
    trending_repos = githubTrendAPI.get_github_trending()
    if trending_repos:
      # 打印输出
      for story in trending_repos:
            print(f"仓库: {story['repo_name']}")
            print(f"描述: {story['repo_desc']}")
            print(f"star: {story['star']}")
            print(f"fork: {story['fork']}")
            print(f"语言: {story['language']}")
            print("-" * 80)     
      # 导出到Markdown文件
      githubTrendAPI.export_daily_github_trend(trending_repos)
    else:
        print("未爬取到任何仓库数据")