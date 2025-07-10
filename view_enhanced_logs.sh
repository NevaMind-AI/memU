#!/bin/bash

# PersonaLab Enhanced Logging Viewer
# 演示如何查看增强的日志信息

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}🔍 PersonaLab Enhanced Logging Viewer${NC}"
echo -e "${BLUE}=================================================${NC}"
echo

# Check if server is running
if ! lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Server not running!${NC}"
    echo -e "${YELLOW}💡 Please start the server first:${NC}"
    echo -e "   cd server && ./start-all.sh"
    exit 1
fi

echo -e "${GREEN}✅ Server is running on port 8000${NC}"
echo

# Check if log file exists
LOG_FILE="/Users/chenhong/project/PersonaLab/server/backend/server.log"
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}❌ Log file not found: $LOG_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Log file found: $LOG_FILE${NC}"
echo

# Show options
echo -e "${YELLOW}📋 Available logging options:${NC}"
echo -e "${BLUE}1. View recent logs${NC}"
echo -e "${BLUE}2. Monitor real-time logs${NC}"
echo -e "${BLUE}3. Monitor memory update logs only${NC}"
echo -e "${BLUE}4. Send test request and view logs${NC}"
echo -e "${BLUE}5. Exit${NC}"
echo

while true; do
    echo -e "${YELLOW}Choose an option (1-5): ${NC}"
    read -r choice
    
    case $choice in
        1)
            echo -e "\n${GREEN}📄 Recent logs (last 30 lines):${NC}"
            echo "================================"
            tail -30 "$LOG_FILE"
            echo
            ;;
        2)
            echo -e "\n${GREEN}🔄 Real-time log monitoring (Press Ctrl+C to stop):${NC}"
            echo "================================"
            tail -f "$LOG_FILE"
            ;;
        3)
            echo -e "\n${GREEN}🧠 Memory update logs only (Press Ctrl+C to stop):${NC}"
            echo "================================"
            tail -f "$LOG_FILE" | grep -E "(MEMORY_UPDATE|PIPELINE)"
            ;;
        4)
            echo -e "\n${GREEN}🧪 Sending test request...${NC}"
            curl -s -X POST -H "Content-Type: application/json" \
                -d '{"agent_id": "demo_agent", "user_id": "demo_user", "conversation": [{"user_message": "测试增强日志功能", "ai_response": "这会触发详细的流水线日志输出"}]}' \
                http://localhost:8000/api/memories/update-memory > /dev/null
            
            echo -e "${GREEN}✅ Test request sent!${NC}"
            echo -e "${YELLOW}📋 Recent memory update logs:${NC}"
            echo "================================"
            tail -50 "$LOG_FILE" | grep -E "(MEMORY_UPDATE|PIPELINE)" | tail -20
            echo
            ;;
        5)
            echo -e "\n${GREEN}👋 Goodbye!${NC}"
            break
            ;;
        *)
            echo -e "${RED}❌ Invalid option. Please choose 1-5.${NC}"
            ;;
    esac
done 