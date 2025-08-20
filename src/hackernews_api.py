import requests
from bs4 import BeautifulSoup

class HackerNewsAPI:
    def __init__(self):
        self.url = 'https://news.ycombinator.com/newest'
        
    def get_hackernews_latest(self):
        
        try:
            # 发送请求获取页面内容
            response = requests.get(self.url)
            response.raise_for_status()  # 检查请求是否成功
            
            # 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有热点条目
            stories = []
            # HackerNews 的条目使用 class 为 "athing" 的 tr 标签
            for item in soup.select('tr.athing'):
                # 获取排名
                rank = item.select_one('.rank').get_text(strip=True).replace('.', '')
                
                # 获取标题和链接
                title_tag = item.select_one('.title a')
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                
                # 验证链接协议
                if not link.startswith(('http://', 'https://')):
                    continue
                
                # 获取下一行的额外信息（作者、时间等）
                next_row = item.find_next_sibling('tr')
                comment_count = '0'
                if next_row:
                    # 获取作者
                    author = next_row.select_one('.hnuser')
                    author = author.get_text(strip=True) if author else 'Unknown'
                    
                    # 获取评论数
                    # 查找包含评论数的 <a> 标签
                    comment_links = next_row.select('.subtext a')
                    for comment_link in comment_links:
                        link_text = comment_link.get_text(strip=True)
                        if 'comment' in link_text:
                            comment_count = link_text.split()[0]
                            break
                
                stories.append({
                    'rank': rank,
                    'title': title,
                    'link': link,
                    'author': author,
                    'comments': comment_count
                })
            
            return stories
        
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
        except Exception as e:
            print(f"解析错误: {e}")
            return None

if __name__ == "__main__":
    hackerNewsAPI = HackerNewsAPI()
    latest_stories = hackerNewsAPI.get_hackernews_latest()
    
    if latest_stories:
        print(f"HackerNews 最新热点：共获取到{len(latest_stories)}条热点\n")
        for story in latest_stories:
            print(f"排名: {story['rank']}")
            print(f"标题: {story['title']}")
            print(f"链接: {story['link']}")
            print(f"作者: {story['author']}")
            print(f"评论数: {story['comments']}")
            print("-" * 80)
    else:
        print("无法获取 HackerNews 最新热点")
