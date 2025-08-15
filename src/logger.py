from loguru import logger
import sys

# 移除默认配置，便于自定义配置
logger.remove()
# 增加到输出到控制台的日志，格式化输出
logger.add(sys.stdout, level="DEBUG", format="{time} {level} {message}", colorize=True)
logger.add(sys.stderr, level="ERROR", format="{time} {level} {message}", colorize=True)
# 输出到文件的日志
logger.add("logs/app.log", rotation="2 MB", level="DEBUG")

LOG = logger

__all__ = ["LOG"]
