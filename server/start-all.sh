#!/bin/bash

# PersonaLab 后台管理系统 - 一键启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印横幅
print_banner() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}🚀 PersonaLab 后台管理系统 (React + FastAPI)${NC}"
    echo -e "${BLUE}=================================================${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 未安装，请先安装 $1${NC}"
        exit 1
    fi
}

# 检查环境
check_environment() {
    echo -e "${YELLOW}🔍 检查运行环境...${NC}"
    
    # 检查Python
    check_command python3
    echo -e "${GREEN}✅ Python: $(python3 --version)${NC}"
    
    # 检查Node.js
    check_command node
    echo -e "${GREEN}✅ Node.js: $(node --version)${NC}"
    
    # 检查npm
    check_command npm
    echo -e "${GREEN}✅ npm: $(npm --version)${NC}"
}

# 安装依赖
install_dependencies() {
    echo -e "${YELLOW}📦 检查并安装依赖...${NC}"
    
    # 后端依赖
    echo -e "${BLUE}📥 检查后端依赖...${NC}"
    cd backend
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "${YELLOW}🔧 创建Python虚拟环境...${NC}"
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    
    # 前端依赖
    echo -e "${BLUE}📥 检查前端依赖...${NC}"
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}🔧 安装前端依赖...${NC}"
        npm install
    fi
    cd ..
}

# 启动后端
start_backend() {
    echo -e "${BLUE}🔧 启动后端服务器...${NC}"
    cd backend
    source venv/bin/activate
    python start.py &
    BACKEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ 后端服务器已启动 (PID: $BACKEND_PID)${NC}"
    echo -e "${GREEN}📍 API接口: http://localhost:8080${NC}"
    echo -e "${GREEN}📍 API文档: http://localhost:8080/docs${NC}"
}

# 启动前端
start_frontend() {
    echo -e "${BLUE}🔧 启动前端服务器...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ 前端服务器已启动 (PID: $FRONTEND_PID)${NC}"
    echo -e "${GREEN}📍 前端界面: http://localhost:5173${NC}"
}

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}🛑 正在停止服务器...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ 后端服务器已停止${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ 前端服务器已停止${NC}"
    fi
    echo -e "${GREEN}👋 再见！${NC}"
    exit 0
}

# 等待用户输入
wait_for_user() {
    echo -e "\n${GREEN}🎉 系统启动完成！${NC}"
    echo -e "${BLUE}📱 前端界面: http://localhost:5173${NC}"
    echo -e "${BLUE}🔧 API文档: http://localhost:8080/docs${NC}"
    echo -e "\n${YELLOW}按 Ctrl+C 停止所有服务${NC}"
    
    # 等待中断信号
    while true; do
        sleep 1
    done
}

# 主函数
main() {
    # 设置中断处理
    trap cleanup SIGINT SIGTERM
    
    print_banner
    
    # 检查环境
    check_environment
    
    # 安装依赖
    install_dependencies
    
    # 等待一下让用户看到信息
    sleep 2
    
    # 启动服务
    start_backend
    sleep 3  # 等待后端启动
    start_frontend
    sleep 2  # 等待前端启动
    
    # 等待用户输入
    wait_for_user
}

# 检查是否在正确的目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ 请在 server 目录下运行此脚本${NC}"
    echo -e "${YELLOW}💡 正确的用法:${NC}"
    echo -e "   cd server"
    echo -e "   ./start-all.sh"
    exit 1
fi

# 运行主函数
main 