#!/bin/bash

# 设置默认分支/标签为v0.7，如果有参数传入则使用参数值
BRANCH_NAME=${1:-v0.7}
IMAGE_TAG="github_argus:$BRANCH_NAME"

echo "将使用镜像: $IMAGE_TAG"

# 定义支持的环境变量列表，GITHUB_TOKEN是必需的
REQUIRED_ENVS=("GITHUB_TOKEN")
OPTIONAL_ENVS=("GMAIL_SPECIAL_PASSWORD" "OPENAI_API_KEY")  # 根据实际情况修改可选变量

# 存储环境变量的数组
ENV_VARS=()

echo -e "\n准备运行 $IMAGE_TAG 镜像..."
echo "----------------------------------------"

# 处理必需的环境变量
for env in "${REQUIRED_ENVS[@]}"; do
    # 检查环境变量是否已设置
    if [ -z "${!env}" ]; then
        read -p "请输入 $env 的值: " value
        ENV_VARS+=("-e" "$env=$value")
    else
        ENV_VARS+=("-e" "$env=${!env}")
        echo "$env 已从当前环境变量中获取"
    fi
done

# 处理可选的环境变量
echo -e "\n是否需要设置可选环境变量？"
for env in "${OPTIONAL_ENVS[@]}"; do
    if [ -z "${!env}" ]; then
        read -p "是否设置 $env? (y/n，默认n): " set_env
        if [ "$set_env" = "y" ] || [ "$set_env" = "Y" ]; then
            read -p "请输入 $env 的值: " value
            ENV_VARS+=("-e" "$env=$value")
        fi
    else
        ENV_VARS+=("-e" "$env=${!env}")
        echo "$env 已从当前环境变量中获取"
    fi
done

# 显示即将执行的命令
echo -e "\n即将执行以下命令:"
echo "docker run -it --rm --add-host=host.docker.internal:host-gateway $IMAGE_TAG"

# 执行docker命令
echo -e "\n启动容器..."
docker run -it --rm --add-host=host.docker.internal:host-gateway "${ENV_VARS[@]}" "$IMAGE_TAG"
