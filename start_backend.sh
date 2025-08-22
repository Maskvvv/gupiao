#!/usr/bin/env bash
set -euo pipefail

# 切换到项目根目录（脚本所在位置）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 创建并激活虚拟环境
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 安装/更新依赖
python -m pip install -U pip
pip install -r requirements.txt

# 允许通过环境变量覆盖 HOST/PORT
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}

# 启动 FastAPI 开发服务（热重载）
exec uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload