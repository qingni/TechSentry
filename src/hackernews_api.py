import requests
from bs4 import BeautifulSoup

def get_hackernews_latest():
    # HackerNews 最新热点页面 URL
    url = 'https://news.ycombinator.com/newest'
    
    try:
        # 发送请求获取页面内容
        response = requests.get(url)
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
            
            # 获取下一行的额外信息（作者、时间等）
            next_row = item.find_next_sibling('tr')
            if next_row:
                # 获取作者
                author = next_row.select_one('.hnuser')
                author = author.get_text(strip=True) if author else 'Unknown'
                
                # 获取评论数
                comments = next_row.select_one('.subtext a:last-child')
                if comments and 'comment' in comments.get_text():
                    comment_count = comments.get_text(strip=True).split()[0]
                else:
                    comment_count = '0'
            
            stories.append({
                'rank': rank,
                'title': title,
                'link': link,
                'author': author,
                'comments': comment_count
            })
            
            # 只获取前20条热点
            if len(stories) >= 20:
                break
        
        return stories
    
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
    except Exception as e:
        print(f"解析错误: {e}")
        return None

if __name__ == "__main__":
    latest_stories = get_hackernews_latest()
    
    if latest_stories:
        print("HackerNews 最新热点：\n")
        for story in latest_stories:
            print(f"排名: {story['rank']}")
            print(f"标题: {story['title']}")
            print(f"链接: {story['link']}")
            print(f"作者: {story['author']}")
            print(f"评论数: {story['comments']}")
            print("-" * 80)
    else:
        print("无法获取 HackerNews 最新热点")
