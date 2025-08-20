import requests
from bs4 import BeautifulSoup
import pandas as pd

def crawl_github_trending(url: str) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://github.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
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

if __name__ == "__main__":
    trending_url = "https://github.com/trending?since=daily"
    print("开始爬取GitHub每日趋势仓库...")
    trending_repos = crawl_github_trending(trending_url)
    if trending_repos:
      for story in trending_repos:
          print(f"仓库: {story['repo_name']}")
          print(f"描述: {story['repo_desc']}")
          print(f"star: {story['star']}")
          print(f"fork: {story['fork']}")
          print(f"语言: {story['language']}")
          print("-" * 80)
    else:
        print("未爬取到任何仓库数据")