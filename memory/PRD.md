# LEAMSS Immigration Portal - Product Requirements Document

**Current Version:** 2.3 (All Features Fixed + New Features)
**Last Updated:** April 2, 2026
**Status:** Production Ready

---

## 1. Original Problem Statement
Build a comprehensive immigration service portal (LEAMSS Portal) supporting Admin, Case Manager, Partner, and Client roles. Migrated from MongoDB to MySQL. Features include role-based dashboards, multi-step case workflows, document management, ticketing, analytics, and payment processing.

## 2. Core Architecture
- **Frontend:** React + TailwindCSS + Shadcn UI
- **Backend:** FastAPI + SQLAlchemy (async) + MySQL/MariaDB
- **Database:** MariaDB with full relational schema

## 3. Implemented Features

### Authentication & Roles
- JWT-based auth with role-based access control
- 4 roles: Admin, Case Manager, Partner, Client
- Admin impersonation (switch to any user)

### Admin Dashboard
- Overview stats (pending sales, active cases, revenue, tickets)
- Pending Sales with separate **Approve** and **Reject** buttons (2-step process)
- Client credentials dialog shown on sale approval (for new clients)
- Case manager assignment from Cases page (separate from approval)
- User management with Switch (impersonate) capability
- Products & Workflow management (full CRUD)
- Settings, Notifications, Sales Reports

### Case Manager Dashboard
- My Cases with case detail view
- Workflow step status updates (in_progress/completed)
- Document review (approve/reject with comments)
- **Information Sheet** - comprehensive client profile collection (Personal, Contact, Education, Work, Language, Family, Immigration details)
- Additional document request system
- Support tickets

### Partner Dashboard
- Sales tracking with commission visibility
- Commission reports
- Support tickets

### Client Dashboard
- Case status & workflow progress
- Document uploads
- Support tickets

### Advanced Features
- Analytics Dashboard (sales trends, revenue, top products/partners)
- Global Search (Ctrl+K)
- Activity Log UI (audit trail)
- Partner Sales Report
- Stripe Payment integration (scaffolded)

## 4. Key API Endpoints
- `POST /api/auth/login` - Login
- `POST /api/auth/impersonate/{user_id}` - Admin user switching
- `POST /api/sales/approve` - 2-step approval (no CM required)
- `GET /api/sales/partner-report` - Partner report
- `POST /api/cases/update-step` - Update workflow step
- `PUT /api/cases/{id}/assign-manager` - Assign case manager
- `GET/POST /api/cases/{id}/information-sheet` - Information sheet CRUD
- `POST /api/cases/{id}/custom-document-request` - Request documents
- `GET /api/analytics/*` - Analytics endpoints
- `GET /api/search/global` - Global search

## 5. Changelog

### April 2, 2026 - Version 2.3
- Fixed: update-step endpoint changed from PUT to POST
- Added: GET /api/sales/partner-report endpoint
- Added: POST /api/cases/{id}/custom-document-request endpoint
- Added: ClientInformationSheet model and CRUD endpoints
- Refactored: Sale approval is now 2-step (approve first, assign CM separately)
- Added: Client login credentials returned on sale approval
- Added: Information Sheet dialog in Case Manager dashboard
- Added: Client Credentials dialog in Admin dashboard
- Fixed: Frontend partner-report URL (path param → query param)
- Testing: 30/30 backend tests passed, all frontend features verified

### April 2, 2026 - Version 2.2
- Fixed: Sale approval crashing on null commission_rate
- Fixed: Missing GET /api/sales/{id}/documents endpoint
- Fixed: Missing PUT /api/cases/{id}/assign-manager endpoint
- Fixed: Missing POST /api/auth/impersonate/{id} endpoint
- Fixed: Missing PUT /api/products/{id}/workflow-step/{order} endpoint
- Fixed: SQLAlchemy reserved 'metadata' column name
- Testing: 29/29 backend tests passed

### Earlier Versions
- MongoDB → MySQL backend migration (DONE)
- Fixed database seed scripts (DONE)
- Analytics Dashboard implementation (DONE)
- Global Search functionality (DONE)
- Activity Log UI and Admin Sidebar integration (DONE)

## 6. Remaining Backlog

### P0
- Complete & test Stripe payment flow end-to-end

### P1
- Implement Activity Log backend logging (inject audit events into core routers)
- Wire email notifications to key events (email_service.py exists but not triggered)

### P2
- PDF report generation from frontend
- Bulk document upload

### P3
- SMS Notifications (Twilio)
- Google Calendar Integration
- WhatsApp integration
