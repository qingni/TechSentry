import os
from pathlib import Path
from utils import Utils
from datetime import datetime
from typing import Optional
class ReportGenerator:
    def __init__(self, llm):
        self.llm = llm

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
            
            return file_path
        
        except IOError as e:
            raise Exception(f"Failed to write daily progress file: {str(e)}") from e

    
    def generate_daily_report(self, markdown_file_path):
        # 转换为Path对象，方便路径操作
        input_path = Path(markdown_file_path)
        
        # 检查输入文件是否存在
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path.resolve()}")
        
        # 检查路径是否指向文件（而非目录）
        if not input_path.is_file():
            raise IsADirectoryError(f"路径指向的是目录，而非文件: {input_path.resolve()}")
        
        try:
            # 读取输入文件内容，指定编码
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查文件内容是否为空
            if not content.strip():
                raise ValueError(f"输入文件内容为空: {input_path.resolve()}")
            
            # 调用LLM生成报告
            report = self.llm.generate_daily_report(content, True)
            
            # 生成输出文件路径
            report_file_path = input_path.with_name(f"{input_path.stem}_report.md")
            
            # 确保输出目录存在
            output_dir = input_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入报告文件
            with open(report_file_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"生成的报告已保存至: {report_file_path.resolve()}")
            return report, report_file_path
        
        except UnicodeDecodeError as e:
            raise Exception(f"文件编码错误，无法读取: {input_path.resolve()}") from e
        except Exception as e:
            # 捕获其他可能的异常（如LLM调用失败）
            raise Exception(f"生成日报时发生错误: {str(e)}") from e
        
    
