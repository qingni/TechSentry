#!/bin/bash
set -euo pipefail

IMAGE_REPO="github_argus"

sanitize_tag() {
    local raw_tag="$1"
    local normalized_tag

    normalized_tag=$(echo "$raw_tag" | tr '[:upper:]' '[:lower:]' | sed 's#[^a-z0-9_.-]#-#g' | sed 's#^[.-]*##' | sed 's#[-.]*$##')

    if [ -z "$normalized_tag" ]; then
        normalized_tag="latest"
    fi

    echo "$normalized_tag"
}

# 检查Docker服务是否运行
if ! docker info >/dev/null 2>&1; then
    echo "错误：Docker服务未运行，请先启动Docker"
    exit 1
fi

# 检查是否在Git仓库中
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "错误：当前目录不是Git仓库"
    exit 1
fi

# 优先使用传入参数，否则使用当前分支名
if [ -n "${1:-}" ]; then
    RAW_TAG="$1"
else
    RAW_TAG=$(git rev-parse --abbrev-ref HEAD)
    if [ "$RAW_TAG" = "HEAD" ]; then
        RAW_TAG="detached-$(git rev-parse --short HEAD)"
    fi
fi

TAG=$(sanitize_tag "$RAW_TAG")
IMAGE_TAG="$IMAGE_REPO:$TAG"

if [ "$RAW_TAG" != "$TAG" ]; then
    echo "提示：检测到标签包含特殊字符，已自动规范化: $RAW_TAG -> $TAG"
fi

# 构建Docker镜像
echo "正在构建镜像：$IMAGE_TAG"
if docker build -t "$IMAGE_TAG" .; then
    echo "✅ 镜像构建成功：$IMAGE_TAG"
    echo "运行命令测试：./run-docker.sh $TAG"
else
    echo "❌ 镜像构建失败，请检查Dockerfile配置"
    exit 1
fi
