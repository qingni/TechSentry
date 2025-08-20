# 使用官方Python轻量级镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置容器启动命令
CMD ["python", "src/daemon_process.py"]
