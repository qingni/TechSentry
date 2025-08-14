from command.command_interface import CommandInterface
from command.command_parser import CommandParser

def main():
    cli = CommandInterface()
    parser = CommandParser()
    
    cli.print_help()
    
    while True:
        try:
            user_input = input("GitHub Argus> ").strip()
            if not user_input:
                continue
                
            parsed = parser.parse(user_input)
            if parsed:
                cli.execute_command(parsed.command, parsed.args)
            else:
                print("命令解析错误，请输入 'help' 查看帮助")
                
        except KeyboardInterrupt:
            print("\n使用 'exit' 或 'quit' 命令退出程序")
        except Exception as e:
            print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
