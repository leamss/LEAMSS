#!/bin/bash
# Ensure MariaDB is installed and running, then start backend
which mysqld_safe > /dev/null 2>&1 || apt-get install -y mariadb-server -qq 2>/dev/null
pgrep -x mariadbd > /dev/null || mysqld_safe --datadir=/var/lib/mysql &
sleep 3
mysql -e "CREATE DATABASE IF NOT EXISTS leamss_portal;" 2>/dev/null

cd /app/backend_mysql

# Start uvicorn in background briefly to create tables, then seed if empty
/root/.venv/bin/python -c "
from core.database import sync_engine
from core.models import Base
Base.metadata.create_all(bind=sync_engine)
print('Tables created')
" 2>/dev/null

# Fix payment_method enum
mysql leamss_portal -e "ALTER TABLE sales MODIFY COLUMN payment_method ENUM('cash','bank_transfer','card','cheque','check','upi','online','other') DEFAULT NULL;" 2>/dev/null

# Auto-seed if no users exist
USER_COUNT=$(mysql -N leamss_portal -e "SELECT COUNT(*) FROM users;" 2>/dev/null)
if [ "$USER_COUNT" = "0" ] || [ -z "$USER_COUNT" ]; then
    echo "Database empty, seeding..."
    /root/.venv/bin/python seed_complete.py 2>&1 | tail -5
fi

exec /root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1 --reload
