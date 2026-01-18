# LEAMSS Portal - Deployment Guide (MySQL Version)

## Project Overview
LEAMSS Portal is a comprehensive immigration service management system with four user roles:
- **Admin**: Full system control, user management, reports
- **Case Manager**: Case management, document review, client communication
- **Partner**: Sales management, commission tracking
- **Client**: Document upload, case tracking, support tickets

## Tech Stack
- **Frontend**: React 18 + TailwindCSS + Shadcn UI
- **Backend**: Python FastAPI + SQLAlchemy
- **Database**: MySQL/MariaDB

---

## Part 1: Local Development Setup

### Prerequisites
1. **Node.js** (v18 or higher) - https://nodejs.org/
2. **Python** (v3.10 or higher) - https://www.python.org/
3. **MySQL/MariaDB** - https://dev.mysql.com/downloads/ or https://mariadb.org/download/
4. **Git** - https://git-scm.com/

### Step 1: Database Setup

1. Install MySQL or MariaDB
2. Start the database service:
   - **Windows**: MySQL runs as a service automatically
   - **Mac**: `brew services start mysql` or `brew services start mariadb`
   - **Linux**: `sudo systemctl start mysql` or `sudo systemctl start mariadb`

3. Create the database:
```bash
mysql -u root -p
# Enter your password when prompted

# Create database
CREATE DATABASE leamss_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Exit MySQL
exit
```

### Step 2: Backend Setup

```bash
# Navigate to backend folder
cd backend_mysql

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create/edit `.env` file in the `backend_mysql` folder:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=leamss_portal

JWT_SECRET=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000
UPLOAD_DIR=./uploads

# Optional: Email settings for notifications
GMAIL_EMAIL=
GMAIL_APP_PASSWORD=
SENDER_NAME=LEAMSS Portal
```

### Step 4: Initialize Database

The database tables will be created automatically when you start the server. To seed initial data, run:

```bash
python seed_database.py
```

Or manually create the default users via the API.

### Step 5: Start Backend Server

```bash
# Development mode with hot reload
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`
- API Documentation: `http://localhost:8001/docs`
- Health Check: `http://localhost:8001/api/health`

### Step 6: Frontend Setup

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
yarn install

# Create/edit .env file
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env

# Start development server
yarn start
```

The frontend will be available at `http://localhost:3000`

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

---

## Part 2: Production Deployment

### Option A: Docker Deployment

1. Build Docker images:
```bash
docker-compose build
docker-compose up -d
```

### Option B: Manual Server Deployment

#### Backend (Ubuntu/Debian)

```bash
# Install Python and MySQL client
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip libmysqlclient-dev

# Clone/upload project
cd /var/www
git clone <your-repo> leamss-portal

# Setup backend
cd leamss-portal/backend_mysql
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Setup systemd service
sudo nano /etc/systemd/system/leamss-backend.service
```

Create systemd service:
```ini
[Unit]
Description=LEAMSS Portal Backend
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=/var/www/leamss-portal/backend_mysql
Environment="PATH=/var/www/leamss-portal/backend_mysql/venv/bin"
ExecStart=/var/www/leamss-portal/backend_mysql/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable leamss-backend
sudo systemctl start leamss-backend
```

#### Frontend

```bash
cd /var/www/leamss-portal/frontend

# Build production bundle
yarn install
yarn build

# Serve with nginx
sudo apt install nginx
```

Nginx configuration (`/etc/nginx/sites-available/leamss`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/leamss-portal/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Uploads
    location /uploads {
        proxy_pass http://localhost:8001/uploads;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/leamss /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## API Endpoints Summary

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - Register new user
- `GET /api/auth/me` - Get current user

### Users (Admin only)
- `GET /api/users` - List all users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

### Products
- `GET /api/products` - List products
- `POST /api/products` - Create product (Admin)
- `PUT /api/products/{id}` - Update product (Admin)

### Sales
- `GET /api/sales` - All sales (Admin)
- `GET /api/sales/my-sales` - Partner's sales
- `GET /api/sales/pending` - Pending approvals (Admin)
- `POST /api/sales` - Create sale (Partner)
- `POST /api/sales/approve` - Approve/reject sale (Admin)

### Cases
- `GET /api/cases` - All cases (Admin)
- `GET /api/cases/my-cases` - User's cases
- `GET /api/cases/{id}` - Case details
- `PUT /api/cases/update-step` - Update step status

### Documents
- `GET /api/documents/case/{id}` - Case documents
- `POST /api/documents/upload` - Upload document
- `POST /api/documents/review` - Review document

### Tickets
- `GET /api/tickets/my-tickets` - User's tickets
- `GET /api/tickets/all` - All tickets (Admin)
- `GET /api/tickets/stats` - Ticket statistics
- `POST /api/tickets` - Create ticket
- `POST /api/tickets/{id}/message` - Add message

### Statistics
- `GET /api/stats/dashboard` - Admin dashboard stats
- `GET /api/stats/partner-dashboard` - Partner stats
- `GET /api/stats/case-manager-dashboard` - Case manager stats
- `GET /api/stats/client-dashboard` - Client stats

### Reports (Admin)
- `GET /api/reports/sales` - Sales report
- `GET /api/reports/commission` - Commission report
- `GET /api/reports/partner-commissions` - Partner commissions summary

---

## Troubleshooting

### Database Connection Issues
- Verify MySQL/MariaDB is running: `sudo systemctl status mysql`
- Check credentials in `.env` file
- Ensure database exists: `mysql -u root -p -e "SHOW DATABASES;"`

### Backend Won't Start
- Check logs: `journalctl -u leamss-backend -f`
- Verify all dependencies: `pip install -r requirements.txt`
- Check port availability: `lsof -i :8001`

### Frontend Issues
- Clear node_modules and reinstall: `rm -rf node_modules && yarn install`
- Check REACT_APP_BACKEND_URL in `.env`
- Verify backend is accessible from browser

---

## Support

For issues or questions, please contact the development team or create a support ticket in the portal.
