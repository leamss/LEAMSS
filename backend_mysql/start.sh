#!/bin/bash
# Ensure MariaDB is installed and running before backend starts
which mysqld_safe > /dev/null 2>&1 || apt-get install -y mariadb-server -qq 2>/dev/null
pgrep -x mariadbd > /dev/null || mysqld_safe --datadir=/var/lib/mysql &
sleep 3
mysql -e "CREATE DATABASE IF NOT EXISTS leamss_portal;" 2>/dev/null
cd /app/backend_mysql
exec /root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1 --reload
