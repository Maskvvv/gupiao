#!/usr/bin/env bash
set -euo pipefail

# 切换到前端目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/frontend-web"

# 可选：如果设置了 NPM_REGISTRY 则切换镜像源
if [ "${NPM_REGISTRY:-}" != "" ]; then
  npm config set registry "$NPM_REGISTRY"
fi

# 安装依赖（优先使用 package-lock.json 的确定版本）
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

# 启动 Vite 开发服务器（允许通过 PORT 覆盖端口）
exec npm run dev -- --host --port "${PORT:-5173}"