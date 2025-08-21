import os
from pathlib import Path
from utils import Utils
from datetime import datetime
from typing import Optional
from logger import LOG

class ReportGenerator:
    def __init__(self, llm, report_types):
        self.llm = llm
        self.report_types = report_types
        self.prompts = {}
        self.preload_prompt()
        
    def preload_prompt(self):
        """
        预加载prompt
        """
        for report_type in self.report_types:
            prompt_file = f"prompts/{report_type}_{self.llm.model_type}.txt"
            if not os.path.exists(prompt_file):
                LOG.error(f"prompt文件未找到: {prompt_file}")
                raise FileNotFoundError(f"prompt文件未找到: {prompt_file}")
            with open(prompt_file, 'r', encoding='utf-8') as f:
                self.prompts[report_type] = f.read()
                
    
    def generate_daily_report(self, markdown_file_path):
        # 转换为Path对象，方便路径操作
        input_path = Path(markdown_file_path)
        
        # 检查输入文件是否存在
        if not input_path.exists():
            LOG.error(f"输入文件不存在: {input_path.resolve()}")
            raise FileNotFoundError(f"输入文件不存在: {input_path.resolve()}")
        
        # 检查路径是否指向文件（而非目录）
        if not input_path.is_file():
            LOG.error(f"路径指向的是目录，而非文件: {input_path.resolve()}")
            raise IsADirectoryError(f"路径指向的是目录，而非文件: {input_path.resolve()}")
        
        try:
            # 读取输入文件内容，指定编码
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查文件内容是否为空
            if not content.strip():
                LOG.error(f"输入文件内容为空: {input_path.resolve()}")
                raise ValueError(f"输入文件内容为空: {input_path.resolve()}")
            
            # 调用LLM生成报告
            report = self.llm.generate_daily_report(content, False)
            
            # 生成输出文件路径
            report_file_path = input_path.with_name(f"{input_path.stem}_report.md")
            
            # 确保输出目录存在
            output_dir = input_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入报告文件
            with open(report_file_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            LOG.info(f"生成的报告已保存至: {report_file_path.resolve()}")
            return report, str(report_file_path)
        
        except UnicodeDecodeError as e:
            LOG.error(f"文件编码错误，无法读取: {input_path.resolve()}")
            raise Exception(f"文件编码错误，无法读取: {input_path.resolve()}") from e
        except Exception as e:
            # 捕获其他可能的异常（如LLM调用失败）
            LOG.error(f"生成日报时发生错误: {str(e)}")
            raise Exception(f"生成日报时发生错误: {str(e)}") from e
        
    
