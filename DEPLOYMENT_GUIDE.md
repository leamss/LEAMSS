# LEAMSS Portal - Deployment Guide

## Project Overview
LEAMSS Portal is a comprehensive immigration service management system with four user roles:
- **Admin**: Full system control, user management, reports
- **Case Manager**: Case management, document review, client communication
- **Partner**: Sales management, commission tracking
- **Client**: Document upload, case tracking, support tickets

## Tech Stack
- **Frontend**: React 18 + Vite + TailwindCSS + Shadcn UI
- **Backend**: Python FastAPI
- **Database**: MongoDB

---

## Part 1: Local Development Setup (VS Code)

### Prerequisites
1. **Node.js** (v18 or higher) - https://nodejs.org/
2. **Python** (v3.10 or higher) - https://www.python.org/
3. **MongoDB** - https://www.mongodb.com/try/download/community
4. **VS Code** - https://code.visualstudio.com/
5. **Git** - https://git-scm.com/

### Step 1: Extract the Project
```bash
# Unzip the project
unzip leamss-portal.zip -d leamss-portal
cd leamss-portal
```

### Step 2: Setup MongoDB
1. Install MongoDB Community Edition
2. Start MongoDB service:
   - **Windows**: MongoDB runs as a service automatically
   - **Mac**: `brew services start mongodb-community`
   - **Linux**: `sudo systemctl start mongod`

3. Verify MongoDB is running:
```bash
mongosh
# You should see the MongoDB shell
```

### Step 3: Backend Setup
```bash
# Navigate to backend folder
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example or create new)
```

Create `backend/.env` file:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=leamss_portal
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
```

**Note on Gmail App Password:**
1. Go to Google Account → Security → 2-Step Verification (enable if not)
2. Go to App passwords → Generate new app password
3. Use that 16-character password in GMAIL_APP_PASSWORD

```bash
# Run backend server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend will run at: `http://localhost:8001`

### Step 4: Frontend Setup
```bash
# Open new terminal, navigate to frontend folder
cd frontend

# Install dependencies
yarn install
# OR if you prefer npm:
npm install

# Create .env file
```

Create `frontend/.env` file:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

```bash
# Run frontend development server
yarn dev
# OR
npm run dev
```

Frontend will run at: `http://localhost:3000`

### Step 5: Initialize Database with Default Users
Open a new terminal and run:
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows

python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def create_default_users():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['leamss_portal']
    
    users = [
        {'id': 'admin001', 'email': 'admin@leamss.com', 'password': pwd_context.hash('Admin@123'), 'name': 'Admin User', 'role': 'admin', 'status': 'active'},
        {'id': 'manager001', 'email': 'manager@leamss.com', 'password': pwd_context.hash('Manager@123'), 'name': 'Case Manager', 'role': 'case_manager', 'status': 'active'},
        {'id': 'partner001', 'email': 'partner@leamss.com', 'password': pwd_context.hash('Partner@123'), 'name': 'Partner User', 'role': 'partner', 'status': 'active', 'commission_rate': 10},
        {'id': 'client001', 'email': 'client@leamss.com', 'password': pwd_context.hash('Client@123'), 'name': 'Client User', 'role': 'client', 'status': 'active'},
    ]
    
    for user in users:
        existing = await db.users.find_one({'email': user['email']})
        if not existing:
            await db.users.insert_one(user)
            print(f'Created user: {user[\"email\"]}')
        else:
            print(f'User already exists: {user[\"email\"]}')
    
    print('Default users created!')

asyncio.run(create_default_users())
"
```

### Step 6: Access the Application
Open browser and go to: `http://localhost:3000`

**Default Login Credentials:**
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

---

## Part 2: Production Deployment (MilesWeb / VPS Server)

### Option A: Deploy on MilesWeb VPS

#### Prerequisites
- MilesWeb VPS with Ubuntu 20.04/22.04
- SSH access to the server
- Domain name (optional but recommended)

#### Step 1: Connect to Server
```bash
ssh root@your-server-ip
```

#### Step 2: Update System & Install Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs

# Install Python 3.10+
apt install -y python3 python3-pip python3-venv

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list
apt update
apt install -y mongodb-org
systemctl start mongod
systemctl enable mongod

# Install Nginx
apt install -y nginx

# Install PM2 for process management
npm install -g pm2 yarn
```

#### Step 3: Upload Project Files
```bash
# On your local machine, upload the zip file
scp leamss-portal.zip root@your-server-ip:/var/www/

# On server
cd /var/www
unzip leamss-portal.zip -d leamss-portal
cd leamss-portal
```

#### Step 4: Setup Backend
```bash
cd /var/www/leamss-portal/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create production .env
nano .env
```

Add to `.env`:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=leamss_portal
JWT_SECRET=generate-a-long-random-secret-key-here
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

Create PM2 ecosystem file:
```bash
nano ecosystem.config.js
```

```javascript
module.exports = {
  apps: [{
    name: 'leamss-backend',
    script: 'venv/bin/uvicorn',
    args: 'server:app --host 0.0.0.0 --port 8001',
    cwd: '/var/www/leamss-portal/backend',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

Start backend:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

#### Step 5: Setup Frontend
```bash
cd /var/www/leamss-portal/frontend

# Create production .env
nano .env
```

Add to `.env`:
```env
REACT_APP_BACKEND_URL=https://yourdomain.com
```
(Or use your server IP: `http://your-server-ip`)

```bash
# Install dependencies and build
yarn install
yarn build
```

#### Step 6: Configure Nginx
```bash
nano /etc/nginx/sites-available/leamss
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    # Or use: server_name your-server-ip;

    # Frontend - React app
    location / {
        root /var/www/leamss-portal/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
        
        # For file uploads
        client_max_body_size 50M;
    }

    # SSE endpoint for notifications
    location /api/notifications/stream {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Cache-Control 'no-cache';
        proxy_set_header X-Accel-Buffering 'no';
        proxy_buffering off;
        chunked_transfer_encoding off;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/leamss /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

#### Step 7: Setup SSL (HTTPS) - Recommended
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

#### Step 8: Initialize Database
```bash
cd /var/www/leamss-portal/backend
source venv/bin/activate

python3 -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def create_default_users():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['leamss_portal']
    
    users = [
        {'id': 'admin001', 'email': 'admin@leamss.com', 'password': pwd_context.hash('Admin@123'), 'name': 'Admin User', 'role': 'admin', 'status': 'active'},
        {'id': 'manager001', 'email': 'manager@leamss.com', 'password': pwd_context.hash('Manager@123'), 'name': 'Case Manager', 'role': 'case_manager', 'status': 'active'},
        {'id': 'partner001', 'email': 'partner@leamss.com', 'password': pwd_context.hash('Partner@123'), 'name': 'Partner User', 'role': 'partner', 'status': 'active', 'commission_rate': 10},
        {'id': 'client001', 'email': 'client@leamss.com', 'password': pwd_context.hash('Client@123'), 'name': 'Client User', 'role': 'client', 'status': 'active'},
    ]
    
    for user in users:
        existing = await db.users.find_one({'email': user['email']})
        if not existing:
            await db.users.insert_one(user)
            print(f'Created user: {user[\"email\"]}')

asyncio.run(create_default_users())
"
```

#### Step 9: Firewall Setup
```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
```

### Option B: Deploy on MilesWeb Shared Hosting (cPanel)

**Note:** Shared hosting has limitations for Python/Node.js apps. VPS is recommended.

If you must use shared hosting:
1. Check if your plan supports Node.js/Python
2. Use cPanel's "Setup Node.js App" feature
3. Use cPanel's "Setup Python App" feature
4. Configure .htaccess for routing

---

## Part 3: Maintenance & Troubleshooting

### View Logs
```bash
# Backend logs
pm2 logs leamss-backend

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# MongoDB logs
tail -f /var/log/mongodb/mongod.log
```

### Restart Services
```bash
# Restart backend
pm2 restart leamss-backend

# Restart Nginx
systemctl restart nginx

# Restart MongoDB
systemctl restart mongod
```

### Update Application
```bash
cd /var/www/leamss-portal

# Pull new code or upload new zip
# Then rebuild frontend
cd frontend
yarn build

# Restart backend
pm2 restart leamss-backend
```

### Backup Database
```bash
# Create backup
mongodump --db leamss_portal --out /backup/$(date +%Y%m%d)

# Restore backup
mongorestore --db leamss_portal /backup/20260117/leamss_portal
```

---

## Part 4: VS Code Development Tips

### Recommended Extensions
1. **Python** - Microsoft
2. **Pylance** - Microsoft
3. **ES7+ React/Redux/React-Native snippets**
4. **Tailwind CSS IntelliSense**
5. **MongoDB for VS Code**
6. **Thunder Client** (API testing)

### VS Code Tasks (`.vscode/tasks.json`)
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Backend",
      "type": "shell",
      "command": "cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8001",
      "group": "build"
    },
    {
      "label": "Start Frontend",
      "type": "shell",
      "command": "cd frontend && yarn dev",
      "group": "build"
    }
  ]
}
```

### Debugging Configuration (`.vscode/launch.json`)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["server:app", "--reload", "--port", "8001"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      }
    }
  ]
}
```

---

## Support & Contact

For any issues or questions:
1. Check the logs first
2. Verify all environment variables are set correctly
3. Ensure MongoDB is running
4. Check firewall/port settings

**Default Credentials (Change in Production!):**
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

---

## Security Checklist for Production

- [ ] Change all default passwords
- [ ] Generate strong JWT_SECRET
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall
- [ ] Set up regular backups
- [ ] Enable MongoDB authentication
- [ ] Review and restrict CORS settings
- [ ] Set up monitoring (e.g., PM2 monitoring, Uptime Robot)
