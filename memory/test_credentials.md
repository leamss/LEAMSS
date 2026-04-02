# LEAMSS Portal - Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |
| Client 2 | client2@leamss.com | Client@123 |

## Notes
- When a sale is approved for a NEW client, their login credentials are `Client@123` (shown in the credentials dialog after approval)
- The database uses MySQL/MariaDB — run `apt-get install -y mariadb-server && mysqld_safe &` if DB is down
- Re-seed with `cd /app/backend_mysql && python seed_complete.py`
