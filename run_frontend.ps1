# 前端项目启动脚本
# 切换到前端目录
Set-Location "$PSScriptRoot\frontend-web"

# 检查 node_modules 是否存在，如果不存在则安装依赖
if (-not (Test-Path "node_modules")) {
    Write-Host "正在安装前端依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败!" -ForegroundColor Red
        exit 1
    }
    Write-Host "依赖安装完成!" -ForegroundColor Green
}

# 启动前端开发服务器
Write-Host "正在启动前端开发服务器..." -ForegroundColor Green
npm run dev