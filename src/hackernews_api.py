import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from logger import LOG

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

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
            
    def export_hours_hack_news(self, stories, output_dir="hacker_news"):
        """导出热点条目到Markdown文件"""
        try:
            # 创建日期目录（上海时区）
            now = datetime.now(SHANGHAI_TZ)
            today = now.strftime("%Y-%m-%d")
            hour = now.strftime("%H")
            date_dir = os.path.join(output_dir, today)
            os.makedirs(date_dir, exist_ok=True)
            
            # 创建文件路径
            file_path = os.path.join(date_dir, f"{hour}.md")
            
            # 写入Markdown内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# HackerNews 热点 {today} {hour}:00\n\n")
                for story in stories:
                    f.write(f"## {story['rank']}. [{story['title']}]({story['link']})\n")
                    f.write(f"- 作者: {story['author']}\n")
                    f.write(f"- 评论数: {story['comments']}\n\n")
            
            print(f"✅ 热点已导出到: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"❌ 导出失败: {str(e)}")
            return None
            
    def generate_daily_report(self, output_dir="hacker_news", trend_dir="tech_trend"):
        """生成每日报告，汇总当天所有小时文件"""
        try:
            # 获取当天日期（上海时区）
            today = datetime.now(SHANGHAI_TZ).strftime("%Y-%m-%d")
            # 当天的小时文件目录
            daily_dir = os.path.join(output_dir, today)
            # 汇总目录路径
            trend_dir_path = os.path.join(output_dir, trend_dir)
            os.makedirs(trend_dir_path, exist_ok=True)
            # 汇总文件路径
            report_file_path = os.path.join(trend_dir_path, f"{today}.md")
            
            # 检查当天目录是否存在
            if not os.path.exists(daily_dir):
                print(f"❌ 当日目录不存在: {daily_dir}")
                return None
            
            # 获取并处理小时文件
            hour_files = []
            for filename in os.listdir(daily_dir):
                if filename.endswith("_report.md"):
                    base_name = filename.replace("_report.md", "")
                    if base_name.isdigit():
                        hour_files.append((int(base_name), filename))
            
            if not hour_files:
                LOG.warning(f"⚠️ 未找到有效的小时报告文件")
                return None
            
            # 按小时排序
            hour_files.sort(key=lambda x: x[0])
            LOG.info(f"找到 {len(hour_files)} 个有效小时文件，将按时间顺序处理：{hour_files}")
            
            # 生成汇总报告
            try:
                with open(report_file_path, "w", encoding="utf-8") as report_file:
                    report_file.write(f"# HackerNews 每日热点汇总 {today}\n\n")
                    
                    processed_count = 0
                    for hour, filename in hour_files:
                        file_path = os.path.join(daily_dir, filename)
                        
                        if not os.path.exists(file_path):
                            LOG.warning(f"文件不存在，跳过: {file_path}")
                            continue
                        
                        try:
                            with open(file_path, "r", encoding="utf-8") as hour_file:
                                content = hour_file.read()
                            
                            report_file.write(f"## {hour}:00 热点\n\n")
                            report_file.write(content)
                            report_file.write("\n")
                            processed_count += 1
                        except Exception as e:
                            LOG.error(f"处理文件 {file_path} 时出错: {str(e)}")
                    
                    LOG.info(f"成功处理 {processed_count}/{len(hour_files)} 个文件")
                
                LOG.info(f"✅ 每日报告已生成: {report_file_path}")
                return report_file_path
                
            except Exception as e:
                LOG.error(f"❌ 生成每日报告失败: {str(e)}")
                return None
            
        except Exception as e:
            LOG.error(f"❌ 生成每日报告失败: {str(e)}")
            return None

if __name__ == "__main__":
    hackerNewsAPI = HackerNewsAPI()
    latest_stories = hackerNewsAPI.get_hackernews_latest()
    
    if latest_stories:
        print(f"HackerNews 最新热点：共获取到{len(latest_stories)}条热点\n")
        # 导出到小时Markdown文件
        export_path = hackerNewsAPI.export_hours_hack_news(latest_stories)
        # 生成每日报告
        if export_path:
            hackerNewsAPI.generate_daily_report()
        for story in latest_stories:
            print(f"排名: {story['rank']}")
            print(f"标题: {story['title']}")
            print(f"链接: {story['link']}")
            print(f"作者: {story['author']}")
            print(f"评论数: {story['comments']}")
            print("-" * 80)
    else:
        print("无法获取 HackerNews 最新热点")
