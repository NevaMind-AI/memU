#!/bin/bash
# PersonaLab Database Cleanup Script
# 
# Usage:
#   ./scripts/clear_database.sh

echo "🗑️  Clearing PersonaLab PostgreSQL database..."

# Source environment variables
source setup_postgres_env.sh

# Connect to database and drop all tables
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
-- Drop all PersonaLab tables
DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS memory_contents CASCADE; 
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS embedding_vectors CASCADE;

-- Optional: Drop any other tables you might have
-- DROP TABLE IF EXISTS your_custom_table CASCADE;

SELECT 'All PersonaLab tables have been dropped!' as result;
"

echo "✅ Database cleanup completed!"
echo "💡 Next time you run PersonaLab, new tables will be created automatically." 