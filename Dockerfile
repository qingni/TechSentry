# 使用官方Python轻量级镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，提升Docker缓存命中率
COPY requirements.txt ./

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目文件
COPY . .

# 设置容器启动命令
CMD ["python", "src/daemon_process.py"]
