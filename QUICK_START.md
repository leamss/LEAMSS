# LEAMSS Immigration Portal - Quick Start

## 🚀 Access the Portal

**URL**: http://localhost:3000 (or your deployment URL)

## 🔐 Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@leamss.com | Admin@123 |
| **Case Manager** | manager@leamss.com | Manager@123 |
| **Partner** | partner@leamss.com | Partner@123 |
| **Client** | client@leamss.com | Client@123 |

## ⚡ Quick Actions

### Admin
1. **Approve Sale** → Pending Sales → Select Case Manager → Assign & Approve
2. **Create Product** → Products → Fill form → Add workflow steps
3. **Add User** → Users → Fill form → Select role → Create

### Partner
1. **Create Sale** → New Sale button → Fill client & payment details → Upload documents
2. **View Commission** → Commission tab → See earnings breakdown

### Case Manager
1. **Update Case** → My Cases → Select case → Update step status
2. **Review Document** → Case details → Documents → Click Review → Approve/Reject

### Client
1. **Upload Document** → Select step → Choose file → Upload
2. **Check Progress** → View checklist with step statuses

## 🏗️ Project Structure

```
/app/
├── backend/          → FastAPI server (port 8001)
├── frontend/         → React app (port 3000)
└── design_guidelines.json
```

## 🛠️ Common Commands

```bash
# Restart services
sudo supervisorctl restart backend frontend

# Check service status
sudo supervisorctl status

# View backend logs
tail -f /var/log/supervisor/backend.err.log

# Seed database with demo data
cd /app/backend && python seed_data.py
```

## 📊 Features Overview

### ✅ Implemented
- 4 role-based portals with JWT authentication
- Sales creation, approval, and commission tracking
- Case management with customizable workflows
- Document upload, review, and approval (GridFS)
- User and product management
- Dashboard statistics for each role
- Role-based access control

### 🔄 Workflow
1. **Partner** creates sale → **Admin** approves → System creates **Client** & **Case**
2. **Client** uploads documents → **Case Manager** reviews → Updates workflow steps
3. **Admin** monitors everything, manages products and users

## 🎨 Design Highlights

- **Professional Swiss Design**: Clean, high-contrast, trustworthy
- **Colors**: Deep Slate primary, Electric Blue accents
- **Fonts**: Merriweather (headings) + Inter (body)
- **Responsive**: Works on desktop, tablet, and mobile

## 🔗 API Endpoints

- `POST /api/auth/login` - Authentication
- `GET /api/products` - List products
- `POST /api/sales` - Create sale (Partner)
- `GET /api/cases/my-cases` - Get assigned cases
- `POST /api/documents/upload` - Upload document
- `GET /api/stats/dashboard` - Dashboard stats

## 📝 Notes

- Database: MongoDB (localhost:27017)
- All passwords use bcrypt hashing
- JWT tokens expire in 24 hours
- Document formats: PDF, JPG, PNG (max 10MB)
- Hot reload enabled for both backend and frontend

## 🆘 Need Help?

1. Check README.md for detailed documentation
2. See USAGE_GUIDE.md for step-by-step instructions
3. Verify all services are running: `sudo supervisorctl status`

---

**Built with ❤️ using FastAPI + React + MongoDB**
