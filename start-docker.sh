#!/bin/bash

# PersonaLab Docker Management System - Backend + Database Startup Script

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
    echo -e "${BLUE}🐳 PersonaLab Docker Management System${NC}"
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
    echo -e "${YELLOW}🔍 Checking Docker environment...${NC}"
    
    # Check Docker
    check_command docker
    echo -e "${GREEN}✅ Docker: $(docker --version)${NC}"
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose: $(docker-compose --version)${NC}"
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose: $(docker compose version)${NC}"
        COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ Docker Compose is not available${NC}"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker daemon is not running. Please start Docker first.${NC}"
        exit 1
    fi
}

# Start services
start_services() {
    echo -e "${YELLOW}🚀 Starting PersonaLab backend services...${NC}"
    
    # Set default OpenAI API key if not set
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set, using empty value${NC}"
        export OPENAI_API_KEY=""
    fi
    
    # Pull images and start services
    echo -e "${BLUE}📦 Pulling latest images...${NC}"
    $COMPOSE_CMD pull postgres
    
    echo -e "${BLUE}🔧 Building and starting backend & database...${NC}"
    $COMPOSE_CMD up -d --build
    
    echo -e "${GREEN}✅ Backend services started successfully!${NC}"
}

# Check service status
check_services() {
    echo -e "${YELLOW}🔍 Checking service status...${NC}"
    
    # Wait for services to be ready
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep 10
    
    # Check if services are running
    if $COMPOSE_CMD ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Backend and database are running!${NC}"
        
        # Test backend API
        if curl -s http://localhost:8000/ > /dev/null; then
            echo -e "${GREEN}✅ Backend API is responding correctly!${NC}"
            
            # Show service URLs
            echo -e "\n${GREEN}🌐 Service URLs:${NC}"
            echo -e "${BLUE}🔧 Backend API: http://localhost:8000${NC}"
            echo -e "${BLUE}📚 API Docs: http://localhost:8000/docs${NC}"
            echo -e "${BLUE}🗄️ Database: localhost:5432${NC}"
            
            # Show frontend instructions
            echo -e "\n${YELLOW}📱 Frontend Setup:${NC}"
            echo -e "To start the frontend, run these commands in a new terminal:"
            echo -e "${BLUE}   cd server/frontend${NC}"
            echo -e "${BLUE}   npm install${NC}"
            echo -e "${BLUE}   npm run dev${NC}"
            echo -e "Then visit: ${BLUE}http://localhost:5173${NC}"
            
        else
            echo -e "${RED}❌ Backend API is not responding${NC}"
            echo -e "${YELLOW}Checking logs...${NC}"
            $COMPOSE_CMD logs backend --tail=20
        fi
        
        # Show useful commands
        echo -e "\n${YELLOW}💡 Useful Commands:${NC}"
        echo -e "   📊 Check status: ${COMPOSE_CMD} ps"
        echo -e "   📜 View logs: ${COMPOSE_CMD} logs -f backend"
        echo -e "   🛑 Stop services: ${COMPOSE_CMD} down"
        echo -e "   🔄 Restart: ${COMPOSE_CMD} restart"
        
    else
        echo -e "${RED}❌ Some services failed to start. Check logs:${NC}"
        $COMPOSE_CMD logs
        exit 1
    fi
}

# Show logs
show_logs() {
    echo -e "\n${YELLOW}📜 Showing service logs (Press Ctrl+C to exit):${NC}"
    $COMPOSE_CMD logs -f
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}✅ Services stopped successfully!${NC}"
    echo -e "${GREEN}👋 Goodbye!${NC}"
    exit 0
}

# Main function
main() {
    # Set interrupt handling
    trap cleanup SIGINT SIGTERM
    
    print_banner
    
    # Check environment
    check_environment
    
    # Start services
    start_services
    
    # Check service status
    check_services
    
    # Ask user if they want to see logs
    echo -e "\n${YELLOW}Would you like to view live logs? (y/N):${NC}"
    read -t 10 -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
    else
        echo -e "${GREEN}🎉 Backend setup complete! Services are running in the background.${NC}"
        echo -e "${YELLOW}Remember to start the frontend manually with the commands shown above.${NC}"
        echo -e "${YELLOW}Use '${COMPOSE_CMD} logs -f backend' to view logs later.${NC}"
    fi
}

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ docker-compose.yml not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Run main function
main 