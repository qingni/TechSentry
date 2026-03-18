import argparse
from dataclasses import dataclass
from typing import Optional, Any
import shlex

@dataclass
class ParsedCommand:
    command: str
    args: Optional[Any] = None  # 存储解析后的参数

class CommandParser:
    def __init__(self):
        # 定义无参数命令列表
        self.no_arg_commands = {'list', 'fetch', 'help', 'exit', 'quit'}
        
        # 创建主解析器
        self.parser = argparse.ArgumentParser(
            description='Tech Sentry 命令行工具',
            add_help=False,
            allow_abbrev=False
        )
        
        # 添加子命令解析器
        self.subparsers = self.parser.add_subparsers(
            dest='command',
            required=True,
            title='可用命令'
        )
        
        # 配置add命令
        add_parser = self.subparsers.add_parser('add', help='添加仓库订阅', add_help=False)
        add_parser.add_argument('--repo', required=True, help='仓库路径 (格式: owner/repo)')
        
        # 配置remove命令
        remove_parser = self.subparsers.add_parser('remove', help='移除仓库订阅', add_help=False)
        remove_parser.add_argument('--repo', required=True, help='仓库路径 (格式: owner/repo)')
        
        # 配置export命令
        export_parser = self.subparsers.add_parser('export', help='导出仓库进度数据', add_help=False)
        export_parser.add_argument('--repo', required=True, help='仓库路径')
        export_parser.add_argument('--since', help='起始日期 (YYYY-MM-DD)')
        export_parser.add_argument('--until', help='结束日期 (YYYY-MM-DD)')
        export_parser.add_argument('--relative', help='相对时间 (如24hours,7d)')
        
        # 配置generate命令
        generate_parser = self.subparsers.add_parser('generate', help='生成每日报告', add_help=False)
        generate_parser.add_argument('--file', required=True, help='输出文件路径')
        
        # 配置无参数命令（明确指定不接受任何参数）
        for cmd in self.no_arg_commands:
            parser = self.subparsers.add_parser(cmd, help=f'{cmd}命令', add_help=False)
            # 禁用所有参数
            parser.set_defaults()

    def parse(self, user_input: str) -> Optional[ParsedCommand]:
        try:
            user_input = user_input.strip()
            if not user_input:
                return None
                
            args_list = shlex.split(user_input)
            command = args_list[0]  # 获取命令名称
            
            # 检查无参数命令是否带有参数
            if command in self.no_arg_commands and len(args_list) > 1:
                raise ValueError(f"'{command}' 命令不接受任何参数，您输入了多余的参数: {', '.join(args_list[1:])}")
            
            # 解析命令和参数
            args = self.parser.parse_args(args_list)
            return ParsedCommand(command=args.command, args=args)
            
        except ValueError as e:
            print(f"参数错误: {str(e)}")
            return None
        except argparse.ArgumentError as e:
            print(f"参数错误: {e.message}")
            return None
        except argparse.UnrecognizedArgumentsError as e:
            print(f"未识别的参数: {', '.join(e.unrecognized_args)}")
            print("请使用 'help' 命令查看支持的参数格式")
            return None
        except Exception as e:
            print(f"解析命令时出错: {str(e)}")
            return None
    