# LEAMSS Immigration Portal - Product Requirements Document

## Overview
LEAMSS Portal is a comprehensive immigration service management system designed to streamline visa consulting and case management operations. The system supports four user roles with distinct capabilities and workflows.

**Current Version:** 2.0 (MySQL)  
**Last Updated:** April 2, 2026  
**Status:** ✅ Production Ready

---

## User Roles & Personas

### 1. Admin
- **Primary Responsibilities**: System oversight, user management, sales approval, reporting
- **Access Level**: Full system access
- **Key Features**: Dashboard with all metrics, user CRUD, product management, commission settings

### 2. Case Manager
- **Primary Responsibilities**: Case processing, document review, client communication
- **Access Level**: Assigned cases and documents
- **Key Features**: Case workflow management, document approval, ticket handling

### 3. Partner
- **Primary Responsibilities**: Client acquisition, sales submission
- **Access Level**: Own sales and referred cases
- **Key Features**: Sales creation, commission tracking, client referrals

### 4. Client
- **Primary Responsibilities**: Document submission, case tracking
- **Access Level**: Own case only
- **Key Features**: Document upload, case status, support tickets

---

## Core Features - All Implemented ✅

### Authentication & Authorization
- [x] JWT-based authentication
- [x] Role-based access control (RBAC)
- [x] Password hashing with bcrypt
- [x] Token expiration (24 hours)

### User Management (Admin)
- [x] CRUD operations for all user types
- [x] Role assignment
- [x] Commission rate configuration for partners
- [x] User status management (active/inactive/suspended)

### Product Management
- [x] Immigration service/visa type configuration
- [x] Fee structure management
- [x] Workflow step definition with required documents
- [x] Commission structure (fixed, percentage, tiered)

### Sales Management
- [x] Partner sale submission with documents
- [x] Admin approval workflow
- [x] Automatic case creation upon approval
- [x] Commission calculation

### Case Management
- [x] Multi-step workflow tracking
- [x] Document requirement per step
- [x] Step status management (locked → pending → in_progress → completed)
- [x] Case assignment to case managers
- [x] Additional document requests

### Document Management
- [x] File upload/download
- [x] Document review workflow (pending_review → approved/rejected)
- [x] Expiry date tracking
- [x] Secure file serving

### Ticketing System
- [x] Multi-role ticket creation
- [x] Message threading
- [x] File attachments
- [x] Status tracking (open → in_progress → resolved → closed)
- [x] Priority levels (low, medium, high, urgent)

### Notifications
- [x] In-app notifications
- [x] Real-time updates via SSE
- [x] Mark read/unread functionality

### Reporting (Admin)
- [x] Dashboard statistics
- [x] Sales reports with date filtering
- [x] Commission reports by partner
- [x] Case status summaries

---

## Technical Architecture

### Backend (MySQL Version)
- **Framework**: FastAPI (Python)
- **Database**: MySQL/MariaDB with SQLAlchemy ORM
- **Authentication**: JWT with python-jose
- **File Storage**: Local filesystem with organized directories

### Frontend
- **Framework**: React 18
- **Styling**: TailwindCSS + Shadcn UI
- **State Management**: React hooks + context
- **HTTP Client**: Axios

### API Endpoints (12 Routers)
1. `/api/auth` - Authentication
2. `/api/users` - User management
3. `/api/products` - Product/service management
4. `/api/sales` - Sales management
5. `/api/cases` - Case management
6. `/api/documents` - Document handling
7. `/api/tickets` - Support tickets
8. `/api/notifications` - Notifications
9. `/api/reports` - Reports and analytics
10. `/api/stats` - Role-specific dashboard stats
11. `/api/scheduler` - Document expiry tracking
12. `/api/settings` - System settings

---

## Testing Status ✅

| Category | Tests | Status |
|----------|-------|--------|
| Authentication | 6/6 | ✅ Pass |
| Users API | 4/4 | ✅ Pass |
| Products API | 5/5 | ✅ Pass |
| Sales API | 4/4 | ✅ Pass |
| Cases API | 5/5 | ✅ Pass |
| Tickets API | 5/5 | ✅ Pass |
| Notifications API | 3/3 | ✅ Pass |
| Documents API | 1/1 | ✅ Pass |
| Reports API | 4/4 | ✅ Pass |
| Role Dashboards | 4/4 | ✅ Pass |
| Health Check | 1/1 | ✅ Pass |
| **Total** | **42/42** | **100%** |

---

## Credentials for Testing

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |
| Client 2 | client2@leamss.com | Client@123 |

---

## File Structure

```
/app
├── backend_mysql/          # MySQL Backend
│   ├── core/
│   │   ├── auth.py         # Authentication utilities
│   │   ├── database.py     # SQLAlchemy configuration
│   │   ├── models.py       # ORM models (23 tables)
│   │   └── schemas.py      # Pydantic schemas
│   ├── routers/            # 12 API route handlers
│   ├── server.py           # FastAPI application
│   ├── seed_complete.py    # Database seeder
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   │   ├── QuickActions.jsx
│   │   │   └── TicketSection.jsx
│   │   └── pages/
│   │       ├── AdminDashboard.jsx
│   │       ├── CaseManagerDashboard.jsx
│   │       ├── PartnerDashboard.jsx
│   │       └── ClientDashboard.jsx
│   └── package.json
├── DEPLOYMENT_GUIDE_MYSQL.md
├── leamss_mysql_schema.sql
└── test_reports/
```

---

## Roadmap / Future Enhancements

### P1 - High Priority
- [ ] Email notifications for key events (sale approval, document review)
- [ ] Payment gateway integration (Stripe/Razorpay)
- [ ] Bulk document upload

### P2 - Medium Priority
- [ ] PDF report generation and export
- [ ] Advanced search and filtering
- [ ] Audit log UI
- [ ] Dashboard analytics with charts

### P3 - Nice to Have
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Google Calendar integration
- [ ] SMS notifications (Twilio)
- [ ] WhatsApp integration

---

## Change Log

### April 2, 2026 - Version 2.0
- ✅ Complete MySQL migration verified
- ✅ All 42 API tests passing
- ✅ All 4 role dashboards working
- ✅ Seed script fixed for correct model fields
- ✅ Full end-to-end testing completed

### January 18, 2026 - Version 2.0 Initial
- ✅ MongoDB to MySQL migration completed
- ✅ SQLAlchemy ORM models created
- ✅ New routers: stats.py, scheduler.py
- ✅ Frontend endpoint fixes for role-specific dashboards

---

## Support

For issues or feature requests, use the in-app ticketing system or contact the development team.
