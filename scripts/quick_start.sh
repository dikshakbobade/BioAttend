#!/bin/bash

# Quick Start Script for Biometric Attendance System
# Sets up the entire development environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Biometric Attendance System - Quick Start Setup       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

MISSING=0
check_command python3 || MISSING=1
check_command pip3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command psql || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${RED}Please install missing dependencies and try again.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All prerequisites found!${NC}"

# Setup Backend
echo ""
echo -e "${YELLOW}Setting up Backend...${NC}"
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -q -r requirements.txt
echo -e "  ${GREEN}✓${NC} Python dependencies installed"

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Generate keys
    SECRET_KEY=$(openssl rand -hex 32)
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Update .env with generated keys (basic sed replacement)
    sed -i "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/" .env
    sed -i "s/your-fernet-encryption-key-for-biometric-templates/$ENCRYPTION_KEY/" .env
    
    echo -e "  ${GREEN}✓${NC} .env file created with generated keys"
    echo -e "  ${YELLOW}!${NC} Remember to update DATABASE_URL in .env"
fi

cd ..

# Setup Frontend
echo ""
echo -e "${YELLOW}Setting up Frontend...${NC}"
cd frontend

npm install --silent
echo -e "  ${GREEN}✓${NC} Node dependencies installed"

cd ..

# Make scripts executable
chmod +x scripts/*.sh
echo -e "  ${GREEN}✓${NC} Scripts made executable"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  Setup Complete!                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Setup PostgreSQL database:"
echo "   ${BLUE}./scripts/setup_database.sh${NC}"
echo ""
echo "2. Update backend/.env with database credentials"
echo ""
echo "3. Run database migrations:"
echo "   ${BLUE}cd backend && source venv/bin/activate && alembic upgrade head${NC}"
echo ""
echo "4. Start the backend server:"
echo "   ${BLUE}cd backend && source venv/bin/activate && uvicorn app.main:app --reload${NC}"
echo ""
echo "5. In another terminal, start the frontend:"
echo "   ${BLUE}cd frontend && npm run dev${NC}"
echo ""
echo "6. Access the dashboard at: ${BLUE}http://localhost:5173${NC}"
echo "   Default login: admin / admin123"
echo ""
