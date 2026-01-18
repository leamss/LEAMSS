# LEAMSS Immigration Portal - Product Requirements Document

## Overview
LEAMSS Portal is a comprehensive immigration service management system designed to streamline visa consulting and case management operations. The system supports four user roles with distinct capabilities and workflows.

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

## Core Requirements

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

### Backend (MySQL Version - CURRENT)
- **Framework**: FastAPI (Python)
- **Database**: MySQL/MariaDB with SQLAlchemy ORM
- **Authentication**: JWT with python-jose
- **File Storage**: Local filesystem with organized directories

### Frontend
- **Framework**: React 18
- **Styling**: TailwindCSS + Shadcn UI
- **State Management**: React hooks + context
- **HTTP Client**: Axios

### Database Schema
- 23 tables with proper relationships
- Foreign key constraints
- Indexed columns for performance
- Stored procedures for complex operations

---

## Implementation Status

### Completed Features (January 2026)
- ✅ Full MongoDB to MySQL migration
- ✅ All CRUD APIs for all entities
- ✅ Role-specific dashboard statistics
- ✅ Document workflow and review system
- ✅ Ticketing system with messaging
- ✅ Real-time notification streaming
- ✅ Commission tracking and reporting
- ✅ Quick Actions widget on dashboards
- ✅ Document expiry tracking

### Testing Status
- ✅ 42/42 backend API tests passing
- ✅ All 4 role dashboards verified
- ✅ Authentication flow tested
- ✅ File upload/download verified

---

## Credentials for Testing

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

---

## API Endpoints Reference

### Authentication
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/auth/change-password`

### Statistics (Role-specific)
- `GET /api/stats/dashboard` - Admin
- `GET /api/stats/partner-dashboard` - Partner
- `GET /api/stats/case-manager-dashboard` - Case Manager
- `GET /api/stats/client-dashboard` - Client

### Resources
- Users: `/api/users`
- Products: `/api/products`
- Sales: `/api/sales`
- Cases: `/api/cases`
- Documents: `/api/documents`
- Tickets: `/api/tickets`
- Notifications: `/api/notifications`
- Reports: `/api/reports`
- Settings: `/api/settings`
- Scheduler: `/api/scheduler`

---

## Roadmap / Future Tasks

### P1 - High Priority
- [ ] Email notifications for key events
- [ ] Web push notifications
- [ ] Bulk document operations

### P2 - Medium Priority
- [ ] Payment gateway integration (Stripe/Razorpay)
- [ ] PDF report generation
- [ ] Advanced search and filtering
- [ ] Audit log UI

### P3 - Nice to Have
- [ ] Mobile app
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Calendar integration

---

## File Structure

```
/app
├── backend_mysql/          # MySQL Backend (Current)
│   ├── core/
│   │   ├── auth.py         # Authentication utilities
│   │   ├── database.py     # SQLAlchemy configuration
│   │   ├── models.py       # ORM models
│   │   └── schemas.py      # Pydantic schemas
│   ├── routers/            # API route handlers
│   ├── server.py           # FastAPI application
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   └── pages/          # Page components
│   └── package.json
├── DEPLOYMENT_GUIDE_MYSQL.md
└── leamss_mysql_schema.sql
```

---

## Change Log

### 2026-01-18
- **MySQL Migration Complete**: Backend fully migrated from MongoDB to MySQL
- **42 Tests Passing**: Comprehensive API test suite
- **Frontend Fixes**: Updated dashboard endpoints for role-specific stats
- **New Routers**: stats.py, scheduler.py added
- **Documentation**: Updated deployment guide for MySQL

---

## Support & Contact

For issues or feature requests, use the in-app ticketing system or contact the development team.
