#!/bin/bash

# 检查Docker服务是否运行
if ! docker info >/dev/null 2>&1; then
    echo "错误：Docker服务未运行，请先启动Docker"
    exit 1
fi

# 获取当前分支名称
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# 检查是否在Git仓库中
if [ $? -ne 0 ]; then
    echo "错误：当前目录不是Git仓库"
    exit 1
fi

# 构建Docker镜像
echo "正在构建镜像：github_argus:$BRANCH_NAME"
docker build -t "github_argus:$BRANCH_NAME" .

# 检查构建结果
if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功：github_argus:$BRANCH_NAME"
    echo "运行命令测试：docker run -it --rm github_argus:$BRANCH_NAME"
else
    echo "❌ 镜像构建失败，请检查Dockerfile配置"
    exit 1
fi