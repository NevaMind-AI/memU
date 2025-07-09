#!/bin/bash

# PersonaLab Backend Management System - One-Click Startup Script

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}🚀 PersonaLab Backend Management System (React + FastAPI)${NC}"
    echo -e "${BLUE}=================================================${NC}"
}

# Check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed, please install $1 first${NC}"
        exit 1
    fi
}

# Check environment
check_environment() {
    echo -e "${YELLOW}🔍 Checking runtime environment...${NC}"
    
    # Check Python
    check_command python3
    echo -e "${GREEN}✅ Python: $(python3 --version)${NC}"
    
    # Check Node.js
    check_command node
    echo -e "${GREEN}✅ Node.js: $(node --version)${NC}"
    
    # Check npm
    check_command npm
    echo -e "${GREEN}✅ npm: $(npm --version)${NC}"
}

# Install dependencies
install_dependencies() {
    echo -e "${YELLOW}📦 Checking and installing dependencies...${NC}"
    
    # Backend dependencies
    echo -e "${BLUE}📥 Checking backend dependencies...${NC}"
    cd backend
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "${YELLOW}🔧 Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    
    # Frontend dependencies
    echo -e "${BLUE}📥 Checking frontend dependencies...${NC}"
    cd frontend
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}🔧 Installing frontend dependencies...${NC}"
        npm install
    fi
    cd ..
}

# Start backend
start_backend() {
    echo -e "${BLUE}🔧 Starting backend server...${NC}"
    cd backend
    source venv/bin/activate
    python start.py &
    BACKEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ Backend server started (PID: $BACKEND_PID)${NC}"
    echo -e "${GREEN}📍 API Interface: http://localhost:8000${NC}"
echo -e "${GREEN}📍 API Documentation: http://localhost:8000/docs${NC}"
}

# Start frontend
start_frontend() {
    echo -e "${BLUE}🔧 Starting frontend server...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo -e "${GREEN}✅ Frontend server started (PID: $FRONTEND_PID)${NC}"
    echo -e "${GREEN}📍 Frontend Interface: http://localhost:5173${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ Backend server stopped${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✅ Frontend server stopped${NC}"
    fi
    echo -e "${GREEN}👋 Goodbye!${NC}"
    exit 0
}

# Wait for user input
wait_for_user() {
    echo -e "\n${GREEN}🎉 System startup completed!${NC}"
    echo -e "${BLUE}📱 Frontend Interface: http://localhost:5173${NC}"
    echo -e "${BLUE}🔧 API Documentation: http://localhost:8000/docs${NC}"
    echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"
    
    # Wait for interrupt signal
    while true; do
        sleep 1
    done
}

# Main function
main() {
    # Set interrupt handling
    trap cleanup SIGINT SIGTERM
    
    print_banner
    
    # Check environment
    check_environment
    
    # Install dependencies
    install_dependencies
    
    # Wait a moment to let user see the information
    sleep 2
    
    # Start services
    start_backend
    sleep 3  # Wait for backend to start
    start_frontend
    sleep 2  # Wait for frontend to start
    
    # Wait for user input
    wait_for_user
}

# Check if running in correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Please run this script in the server directory${NC}"
    echo -e "${YELLOW}💡 Correct usage:${NC}"
    echo -e "   cd server"
    echo -e "   ./start-all.sh"
    exit 1
fi

# Run main function
main 