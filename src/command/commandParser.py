import argparse
import shlex

class CommandParser:
    """命令行解析器"""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='GitHub Argus 命令行工具')
        self.parser.add_argument('command', nargs='?', help='要执行的命令')
        self.parser.add_argument('args', nargs='*', help='命令参数')
    
    def parse(self, input_str: str):
        """解析输入字符串"""
        try:
            return self.parser.parse_args(shlex.split(input_str))
        except SystemExit:
            # 防止argparse在解析错误时退出程序
            return None
