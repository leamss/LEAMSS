# LEAMSS Portal - Deployment Guide

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB 5.0+
- Git (optional)

### Backend Setup

1. Navigate to backend folder:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables in `.env`:
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="leamss_portal"
CORS_ORIGINS="http://localhost:3000,https://yourdomain.com"

# Gmail SMTP (Optional - for email notifications)
GMAIL_EMAIL="your-gmail@gmail.com"
GMAIL_APP_PASSWORD="your-app-password"
SENDER_NAME="LEAMSS Portal"
```

5. Seed initial data (optional):
```bash
python seed_data.py
```

6. Run the backend:
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Setup

1. Navigate to frontend folder:
```bash
cd frontend
```

2. Install dependencies:
```bash
yarn install
# or
npm install
```

3. Configure environment variables in `.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```
For production, set this to your backend API URL.

4. Run the frontend:
```bash
yarn start
# or
npm start
```

### Production Deployment

#### Backend (using Gunicorn + Nginx)

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

3. Nginx configuration:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Frontend (Build for Production)

1. Build the frontend:
```bash
yarn build
# or
npm run build
```

2. Serve with Nginx:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /path/to/frontend/build;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Test Credentials

After running `seed_data.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

## Gmail App Password Setup

To enable email notifications:

1. Go to your Google Account settings
2. Enable 2-Factor Authentication
3. Go to https://myaccount.google.com/apppasswords
4. Generate a new app password for "Mail"
5. Copy the 16-character password
6. Add to backend/.env as `GMAIL_APP_PASSWORD`

## Features

- **Admin Dashboard**: User management, product/workflow editor, sales approval, revenue tracking
- **Partner Portal**: Sales creation, commission tracking
- **Case Manager Portal**: Case management, document review
- **Client Portal**: Document upload, progress tracking
- **Email Notifications**: Automated emails for case updates
- **Flexible Commissions**: Fixed %, Tiered, or Custom per product

## Tech Stack

- **Frontend**: React 18, TailwindCSS, Shadcn UI
- **Backend**: FastAPI, Python 3.11
- **Database**: MongoDB
- **Authentication**: JWT

## Support

For issues or questions, contact the development team.
