#!/bin/sh
set -euo pipefail

# 配置仓库信息及 GitHub API 地址
REPO="thshu/fnos-tv-web"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "正在获取 ${REPO} 的最新发布信息..."
release_data=$(curl -s "${API_URL}")

# 使用 jq 过滤出名称为 "dist.zip" 的发布资产下载链接
zip_url=$(echo "$release_data" | jq -r '.assets[] | select(.name == "dist.zip") | .browser_download_url')

if [[ -z "$zip_url" ]]; then
  echo "错误：未找到名称为 dist.zip 的发布资产。"
  exit 1
fi

echo "发现最新的 dist.zip：${zip_url}"
echo "开始下载 dist.zip ..."
curl -L -o dist.zip "$zip_url"

echo "下载完成。开始解压 dist.zip ..."
unzip -o dist.zip

echo "操作完成。"
