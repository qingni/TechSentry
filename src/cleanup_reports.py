#!/usr/bin/env python3
"""
清理报告文件脚本

功能：
1. 清除daily_progress、github_trend目录中不包含当天日期的文件
2. 删除hacker_news中非当天的目录
3. 清除hacker_news/tech_trend目录中不包含当天日期的文件
"""

import os
import shutil
from datetime import datetime
from logger import LOG

class CleanReportsDir:
    def __init__(self):
        pass
    
    def get_today_date(self):
        """获取当天日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")


    def cleanup_directory(self, directory_path, date_str, is_dir=False, is_time_range=False):
        """
        清理指定目录中的旧文件/目录
        
        :param directory_path: 目标目录路径
        :param date_str: 当天日期字符串
        :param is_dir: 是否处理目录而非文件
        :param is_time_range: 是否处理时间区间格式的文件名
        """
        if not os.path.exists(directory_path):
            LOG.warning(f"目录不存在: {directory_path}")
            return
        
        # 递归遍历所有文件（仅当is_time_range为True时）
        if is_time_range:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.process_time_range_file(file_path, date_str)
            return
        
        # 非递归处理（原有逻辑）
        items = os.listdir(directory_path)
        for item in items:
            item_path = os.path.join(directory_path, item)
            
            # 检查是否为目录（当is_dir=True时）
            if is_dir:
                if os.path.isdir(item_path) and date_str not in item:
                    try:
                        shutil.rmtree(item_path)
                        LOG.info(f"已删除目录: {item_path}")
                    except Exception as e:
                        LOG.error(f"删除目录失败 {item_path}: {e}")
                continue
            
            # 处理普通文件
            if os.path.isfile(item_path):
                should_delete = date_str not in item
                if should_delete:
                    try:
                        os.remove(item_path)
                        LOG.info(f"已删除文件: {item_path}")
                    except Exception as e:
                        LOG.error(f"删除文件失败 {item_path}: {e}")


    def process_time_range_file(self, file_path, date_str):
        """处理时间区间格式的文件"""
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # 移除_report后缀（如果存在）
        if filename.endswith('_report'):
            filename = filename[:-7]
            LOG.debug(f"移除_report后缀后文件名: {filename}")
        
        should_delete = False
        
        if '_' in filename:
            try:
                # 分割时间区间（格式：开始日期_结束日期）
                date_parts = filename.split('_')
                if len(date_parts) >= 2:
                    start_date = date_parts[0]
                    end_date = date_parts[1]
                    
                    # 检查日期格式是否有效（YYYY-MM-DD）
                    if len(start_date) == 10 and len(end_date) == 10:
                        # 检查当天日期是否在区间内
                        if start_date <= date_str <= end_date:
                            LOG.info(f"保留文件（在时间区间内）: {file_path}")
                            return
                        else:
                            should_delete = True
                            LOG.info(f"标记删除（不在时间区间）: {file_path}")
            except Exception as e:
                LOG.error(f"解析时间区间失败 {file_path}: {e}")
                should_delete = True
        else:
            # 文件名不符合区间格式
            should_delete = True
            LOG.info(f"文件名不符合区间格式: {file_path}")
        
        if should_delete:
            try:
                os.remove(file_path)
                LOG.info(f"已删除文件: {file_path}")
            except Exception as e:
                LOG.error(f"删除文件失败 {file_path}: {e}")


    def clean_hacker_news_dirs(self, today_date):
        """清理hacker_news目录下的非当天日期目录，但保留tech_trend目录"""
        hacker_news_dir = 'hacker_news'
        if os.path.exists(hacker_news_dir) and os.path.isdir(hacker_news_dir):
            for subdir in os.listdir(hacker_news_dir):
                # 跳过tech_trend目录
                if subdir == 'tech_trend':
                    LOG.info(f"跳过保留目录: {os.path.join(hacker_news_dir, subdir)}")
                    continue
                    
                subdir_path = os.path.join(hacker_news_dir, subdir)
                if os.path.isdir(subdir_path) and today_date not in subdir:
                    try:
                        shutil.rmtree(subdir_path)
                        LOG.info(f"删除目录: {subdir_path}")
                    except Exception as e:
                        LOG.error(f"删除目录失败: {subdir_path}, 错误: {e}")


    def clean_all_report_dir(self):
        """主清理函数"""
        today = self.get_today_date()
        LOG.info(f"开始清理报告文件，基准日期: {today}")
        
        # 清理daily_progress目录 - 启用时间区间检查
        self.cleanup_directory("daily_progress", today, is_time_range=True)
        
        # 清理github_trend目录 - 普通检查
        self.cleanup_directory("github_trend", today)
        
        # 清理hacker_news目录（删除除tech_trend以外的非当天目录）
        self.clean_hacker_news_dirs(today)
        
        # 清理hacker_news/tech_trend目录 - 普通检查
        self.cleanup_directory(os.path.join("hacker_news", "tech_trend"), today)
        
        LOG.info("清理完成")


if __name__ == "__main__":
    clean_reports = CleanReportsDir()
    clean_reports.clean_all_report_dir()