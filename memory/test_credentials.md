# LEAMSS Portal - Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |
| Client 2 | client2@leamss.com | Client@123 |

## Notes
- New clients created during sale approval get password: `Client@123`
- MariaDB auto-starts via backend start.sh script
- Re-seed: `cd /app/backend_mysql && python seed_complete.py`
- Activity logs track: login, create_sale, sale_approved, update_step, assign_case_manager, upload_document, review_document
