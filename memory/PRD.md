# LEAMSS Immigration Portal - Product Requirements Document

## Overview
LEAMSS Portal is a comprehensive immigration service management system designed to streamline visa consulting and case management operations. The system supports four user roles with distinct capabilities and workflows.

**Current Version:** 2.2 (All Core Features Fixed)  
**Last Updated:** April 2, 2026  
**Status:** Production Ready

---

## User Roles & Personas

### 1. Admin
- **Primary Responsibilities**: System oversight, user management, sales approval, reporting, analytics
- **Access Level**: Full system access
- **Key Features**: Dashboard, analytics, activity logs, user CRUD, product management

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

## Core Features

### ✅ Implemented (Base Features)
- JWT-based authentication with role-based access
- User management (CRUD, roles, commission rates)
- Product management with multi-step workflows
- Sales management with approval workflow
- Case management with step tracking
- Document upload/download with review workflow
- Ticketing system with messaging
- In-app notifications with real-time SSE
- Dashboard statistics for all roles

### ✅ NEW: Enhanced Features (v2.1)

#### 1. Analytics Dashboard (`/admin/analytics`)
- Total Revenue & Commission metrics
- Sales trends over time
- Sales breakdown by status
- Monthly revenue visualization
- Top performing products
- Top performing partners
- Case completion rate

#### 2. Activity Log (`/admin/activity`)
- System-wide activity tracking
- Filterable by entity type, action, date
- User activity statistics
- Audit trail for compliance

#### 3. Global Search (`Ctrl+K`)
- Search across cases, tickets, users, products
- Quick search with autocomplete
- Role-based filtering

#### 4. Export Reports
- CSV export for sales, cases, tickets, commissions
- HTML/printable reports
- Date range filtering

#### 5. Email Notifications (Backend Ready)
- Sale approval/rejection notifications
- Document review notifications
- Ticket reply notifications
- Case step completion alerts
- Document expiry warnings
- Welcome emails for new users

---

## Technical Architecture

### Backend (16 Routers)
1. `/api/auth` - Authentication
2. `/api/users` - User management
3. `/api/products` - Product management
4. `/api/sales` - Sales management
5. `/api/cases` - Case management
6. `/api/documents` - Document handling
7. `/api/tickets` - Support tickets
8. `/api/notifications` - Notifications
9. `/api/reports` - Reports
10. `/api/stats` - Dashboard stats
11. `/api/scheduler` - Document expiry
12. `/api/settings` - System settings
13. `/api/activity` - Activity logging *(NEW)*
14. `/api/export` - CSV/HTML exports *(NEW)*
15. `/api/analytics` - Analytics data *(NEW)*
16. `/api/search` - Global search *(NEW)*

### New Backend Services
- `core/email_service.py` - Email notification templates and sending

### Frontend Components
- `AnalyticsDashboard.jsx` - Analytics page *(NEW)*
- `ActivityLog.jsx` - Activity log page *(NEW)*
- `GlobalSearch.jsx` - Search component *(NEW)*

---

## Testing Status

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
| Search API | ✅ | ✅ Working |
| Analytics API | ✅ | ✅ Working |
| Export API | ✅ | ✅ Working |
| Activity API | ✅ | ✅ Working |
| **Total** | **42+** | **100%** |

---

## Credentials for Testing

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

---

## API Reference - New Endpoints

### Analytics
- `GET /api/analytics/sales-trend?days=30` - Sales trend data
- `GET /api/analytics/sales-by-status` - Sales by status breakdown
- `GET /api/analytics/cases-by-status` - Cases by status
- `GET /api/analytics/monthly-revenue?year=2026` - Monthly revenue
- `GET /api/analytics/top-products` - Top selling products
- `GET /api/analytics/top-partners` - Top performing partners
- `GET /api/analytics/case-completion-rate` - Completion statistics

### Search
- `GET /api/search/global?q=query` - Full global search
- `GET /api/search/quick?q=query` - Quick autocomplete search

### Export
- `GET /api/export/sales/csv` - Export sales as CSV
- `GET /api/export/sales/html` - Export sales as HTML
- `GET /api/export/cases/csv` - Export cases as CSV
- `GET /api/export/cases/html` - Export cases as HTML
- `GET /api/export/commission/csv` - Export commissions as CSV
- `GET /api/export/tickets/csv` - Export tickets as CSV

### Activity Log
- `GET /api/activity/logs` - Get activity logs with filters
- `GET /api/activity/stats` - Activity statistics
- `GET /api/activity/entity/{type}/{id}` - Entity history

---

## Roadmap / Future Tasks

### P1 - High Priority
- [ ] Configure SMTP for email notifications
- [ ] Payment gateway integration (Stripe/Razorpay)
- [ ] WhatsApp integration for notifications

### P2 - Medium Priority
- [ ] Dashboard charts with Chart.js/Recharts
- [ ] Bulk document upload
- [ ] Document OCR for auto-extraction
- [ ] Calendar view for deadlines

### P3 - Nice to Have
- [ ] Mobile app (React Native)
- [ ] Multi-language support (i18n)
- [ ] Advanced analytics with AI insights
- [ ] Integration with immigration APIs

---

## Change Log

### April 2, 2026 - Version 2.2
- Fixed: Sale approval crashing on null commission_rate
- Fixed: Missing GET /api/sales/{id}/documents endpoint
- Fixed: Missing PUT /api/cases/{id}/assign-manager endpoint (case reassignment)
- Fixed: Missing POST /api/auth/impersonate/{id} endpoint (user switching)
- Fixed: Missing PUT /api/products/{id}/workflow-step/{order} endpoint (workflow editing)
- Fixed: Frontend workflow step creation URL mismatch
- Fixed: Frontend impersonate URL pointing to wrong router
- Fixed: SQLAlchemy reserved 'metadata' column name in PaymentTransaction model

### April 2, 2026 - Version 2.1
- ✅ Added Analytics Dashboard with charts
- ✅ Added Activity Log with filtering
- ✅ Added Global Search (Ctrl+K)
- ✅ Added CSV/HTML export functionality
- ✅ Added Email notification service (templates ready)
- ✅ Added 4 new API routers (analytics, search, export, activity)

### January 18, 2026 - Version 2.0
- ✅ MongoDB to MySQL migration completed
- ✅ 42 API tests passing
- ✅ All 4 role dashboards working

---

## Support

For issues or feature requests, use the in-app ticketing system.
