#!/bin/bash
set -euo pipefail

IMAGE_REPO="github_argus"
CONFIG_FILE="config.json"

sanitize_tag() {
    local raw_tag="$1"
    local normalized_tag

    normalized_tag=$(echo "$raw_tag" | tr '[:upper:]' '[:lower:]' | sed 's#[^a-z0-9_.-]#-#g' | sed 's#^[.-]*##' | sed 's#[-.]*$##')

    if [ -z "$normalized_tag" ]; then
        normalized_tag="latest"
    fi

    echo "$normalized_tag"
}

append_env_var() {
    local env_name="$1"
    local required="$2"

    if [ -n "${!env_name:-}" ]; then
        ENV_VARS+=("-e" "$env_name=${!env_name}")
        echo "$env_name 已从当前环境变量中获取"
        return
    fi

    if [ "$required" = "true" ]; then
        read -r -p "请输入 $env_name 的值: " value
        if [ -z "$value" ]; then
            echo "错误：$env_name 不能为空"
            exit 1
        fi
        ENV_VARS+=("-e" "$env_name=$value")
        return
    fi

    read -r -p "是否设置 $env_name? (y/n，默认n): " set_env
    if [ "$set_env" = "y" ] || [ "$set_env" = "Y" ]; then
        read -r -p "请输入 $env_name 的值: " value
        ENV_VARS+=("-e" "$env_name=$value")
    fi
}

if ! docker info >/dev/null 2>&1; then
    echo "错误：Docker服务未运行，请先启动Docker"
    exit 1
fi

# 默认标签策略与构建脚本保持一致：优先参数，其次当前分支，最后latest
if [ -n "${1:-}" ]; then
    RAW_TAG="$1"
else
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        RAW_TAG=$(git rev-parse --abbrev-ref HEAD)
        if [ "$RAW_TAG" = "HEAD" ]; then
            RAW_TAG="detached-$(git rev-parse --short HEAD)"
        fi
    else
        RAW_TAG="latest"
    fi
fi

TAG=$(sanitize_tag "$RAW_TAG")
IMAGE_TAG="$IMAGE_REPO:$TAG"

if [ "$RAW_TAG" != "$TAG" ]; then
    echo "提示：检测到标签包含特殊字符，已自动规范化: $RAW_TAG -> $TAG"
fi

echo "将使用镜像: $IMAGE_TAG"

if ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo "错误：镜像不存在：$IMAGE_TAG"
    echo "请先执行构建：./build-docker.sh ${TAG}"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误：未找到 $CONFIG_FILE，无法判断 model_type"
    exit 1
fi

MODEL_TYPE=$(awk -F'"' '/"model_type"[[:space:]]*:/ {print tolower($4); exit}' "$CONFIG_FILE")
if [ -z "$MODEL_TYPE" ]; then
    echo "错误：config.json 中 llm.model_type 未配置"
    exit 1
fi

echo "检测到 model_type: $MODEL_TYPE"

# 必需变量：GITHUB_TOKEN 为全局必需
REQUIRED_ENVS=("GITHUB_TOKEN")

# 根据 model_type 追加必需变量
case "$MODEL_TYPE" in
    openai)
        REQUIRED_ENVS+=("LLM_API_TOKEN" "LLM_BASE_URL")
        ;;
    ollama)
        ;;
    *)
        echo "错误：不支持的 model_type: $MODEL_TYPE"
        exit 1
        ;;
esac

# 可选变量
OPTIONAL_ENVS=(
    "GMAIL_SPECIAL_PASSWORD"
    "EMAIL_SMTP_SERVER"
    "EMAIL_SMTP_PORT"
    "EMAIL_FROM"
    "EMAIL_TO"
    "WX_WEBHOOK_URL"
)

# 存储环境变量的数组
ENV_VARS=()

echo -e "\n准备运行 $IMAGE_TAG 镜像..."
echo "----------------------------------------"

for env in "${REQUIRED_ENVS[@]}"; do
    append_env_var "$env" "true"
done

echo -e "\n是否需要设置可选环境变量？"
for env in "${OPTIONAL_ENVS[@]}"; do
    append_env_var "$env" "false"
done

echo -e "\n即将执行以下命令:"
echo "docker run -it --rm --add-host=host.docker.internal:host-gateway $IMAGE_TAG"

echo -e "\n启动容器..."
docker run -it --rm --add-host=host.docker.internal:host-gateway "${ENV_VARS[@]}" "$IMAGE_TAG"
