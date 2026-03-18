from command.command_interface import CommandInterface
from command.command_parser import CommandParser
from logger import LOG

def main():
    cli = CommandInterface()
    parser = CommandParser()
    
    cli.print_help()
    
    while True:
        try:
            user_input = input("Tech Sentry> ").strip()
            if not user_input:
                continue
                
            parsed = parser.parse(user_input)
            if parsed:
                cli.execute_command(parsed.command, parsed.args)
            else:
                LOG.error("命令解析错误，请输入 'help' 查看帮助")
                
        except KeyboardInterrupt:
            LOG.error("\n使用 'exit' 或 'quit' 命令退出程序")
        except Exception as e:
            LOG.error(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
