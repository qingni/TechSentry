#!/bin/bash

# Python守护进程管理脚本--by doubao
# 支持启动、停止、查看状态功能

# 配置部分 - 根据实际情况修改
DAEMON_NAME="DaemonProcess"  # 应用名称
PYTHON_SCRIPT="src/daemon_process.py"       # Python脚本路径
VENV_DIR="./venv"            # 虚拟环境目录（如果没有则留空）
LOG_FILE="./logs/$DAEMON_NAME.log"      # 修正：移除赋值语句中的空格
PID_FILE="./logs/$DAEMON_NAME.pid"      # 进程ID文件路径

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "错误：Python脚本 $PYTHON_SCRIPT 不存在！"
    exit 1
fi

# 检查进程是否在运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # 进程运行中
        else
            rm -f "$PID_FILE"  # 清理无效的PID文件
        fi
    fi
    return 1  # 进程未运行
}

# 启动进程
start() {
    if is_running; then
        echo "$DAEMON_NAME 已在运行中 (PID: $(cat $PID_FILE))"
        return 0
    fi

    echo "启动 $DAEMON_NAME ..."
    
    # 确保日志目录存在 [新增]
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$PID_FILE")"
    
    # 准备环境变量和命令
    local cmd
    if [ -n "$VENV_DIR" ] && [ -d "$VENV_DIR" ]; then
        # 使用虚拟环境
        cmd="$VENV_DIR/bin/python3 $PYTHON_SCRIPT"
    else
        # 使用系统默认Python
        cmd="python3 $PYTHON_SCRIPT"
    fi

    # 启动守护进程
    nohup $cmd > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 验证启动是否成功
    sleep 1
    if is_running; then
        echo "$DAEMON_NAME 启动成功 (PID: $pid)"
        echo "日志文件: $LOG_FILE"
    else
        echo "启动失败，请查看日志: $LOG_FILE"
        rm -f "$PID_FILE"
    fi
}

# 停止进程
stop() {
    if ! is_running; then
        echo "$DAEMON_NAME 未在运行中"
        return 0
    fi

    local pid=$(cat "$PID_FILE")
    echo "停止 $DAEMON_NAME (PID: $pid) ..."
    
    # 尝试优雅停止
    kill "$pid"
    local count=0
    while is_running && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done
    
    # 强制终止（如果需要）
    if is_running; then
        echo "优雅停止失败，尝试强制终止..."
        kill -9 "$pid"
        sleep 1
    fi
    
    if is_running; then
        echo "停止失败，请手动检查并终止进程 $pid"
    else
        rm -f "$PID_FILE"
        echo "$DAEMON_NAME 已停止"
    fi
}

# 查看状态
status() {
    if is_running; then
        echo "$DAEMON_NAME 正在运行中 (PID: $(cat $PID_FILE))"
        echo "日志文件: $LOG_FILE"
    else
        echo "$DAEMON_NAME 未在运行中"
    fi
}

# 查看日志
logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "查看 $DAEMON_NAME 日志 (按Ctrl+C退出)..."
        tail -f "$LOG_FILE"
    else
        echo "日志文件不存在: $LOG_FILE"
    fi
}

# 显示帮助信息
usage() {
    echo "使用方法: $0 [命令]"
    echo "命令列表:"
    echo "  start   - 启动守护进程"
    echo "  stop    - 停止守护进程"
    echo "  restart - 重启守护进程"
    echo "  status  - 查看进程状态"
    echo "  logs    - 查看日志输出"
    echo "  help    - 显示帮助信息"
}

# 解析命令参数
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        start
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    help)
        usage
        ;;
    *)
        echo "未知命令: $1"
        usage
        exit 1
        ;;
esac

