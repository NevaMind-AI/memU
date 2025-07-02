#!/bin/bash
# PersonaLab PostgreSQL 环境配置脚本
# 
# 用法:
#   source setup_postgres_env.sh
# 或者:
#   . setup_postgres_env.sh

echo "🔧 配置PersonaLab使用PostgreSQL数据库..."

# 设置PostgreSQL环境变量
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=personalab
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""

# 显示配置信息
echo "✅ PostgreSQL环境变量已设置:"
echo "   POSTGRES_HOST=$POSTGRES_HOST"
echo "   POSTGRES_PORT=$POSTGRES_PORT"
echo "   POSTGRES_DB=$POSTGRES_DB"
echo "   POSTGRES_USER=$POSTGRES_USER"
echo "   POSTGRES_PASSWORD=[空]"

echo ""
echo "🚀 现在PersonaLab将使用PostgreSQL而不是SQLite"
echo "💡 提示: 要永久生效，请将上述export命令添加到 ~/.zshrc 文件中" 