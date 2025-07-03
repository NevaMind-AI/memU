#!/bin/bash
# PersonaLab PostgreSQL Environment Configuration Script
# 
# Usage:
#   source setup_postgres_env.sh
# Or:
#   . setup_postgres_env.sh

echo "🔧 Configuring PersonaLab to use PostgreSQL database..."

# Set PostgreSQL environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=personalab
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""

# Display configuration information
echo "✅ PostgreSQL environment variables have been set:"
echo "   POSTGRES_HOST=$POSTGRES_HOST"
echo "   POSTGRES_PORT=$POSTGRES_PORT"
echo "   POSTGRES_DB=$POSTGRES_DB"
echo "   POSTGRES_USER=$POSTGRES_USER"
echo "   POSTGRES_PASSWORD=[empty]"

echo ""
echo "🚀 PersonaLab is configured to use PostgreSQL database"
echo "💡 Tip: For permanent effect, add the above export commands to your ~/.zshrc file" 