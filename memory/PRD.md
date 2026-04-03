# LEAMSS Immigration Portal - PRD

**Version:** 2.4 | **Updated:** April 3, 2026 | **Status:** Production Ready

## Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, Client roles on FastAPI + MySQL + React.

## Implemented Features (All Tested - 31/31 Backend, 100% Frontend)

### Authentication & Roles
- JWT auth, 4 roles, admin impersonation (switch users)

### Admin Dashboard
- Stats overview, sales with status filter (All/Pending/Approved/Rejected)
- 2-step sale approval: Approve → Assign Case Manager separately
- Client credentials dialog with **Copy/Email/WhatsApp** sharing options
- Products & Workflow CRUD, User management, Commission reports
- Activity Log page with real audit data (logins, actions)
- Partner sales report, global search (Ctrl+K), analytics

### Case Manager Dashboard
- My Cases with detail view, workflow step status updates
- **Information Sheet** - comprehensive client profile (Personal/Contact/Education/Work/Language/Family/Immigration)
- Document review (approve/reject), additional document requests

### Partner Dashboard  
- Create sales with all payment methods (cash, bank_transfer, card, online, check, upi)
- Document upload during sale creation, commission tracking

### Client Dashboard
- Case progress, document uploads, support tickets

### Cross-cutting
- Activity logging on all core actions (login, sales, cases, documents)
- Notifications system, ticketing system
- PDF/CSV export, document upload/download

## Key Endpoints
- `POST /api/auth/login`, `/api/auth/impersonate/{id}`
- `POST /api/sales` (multipart), `POST /api/sales/approve`
- `POST /api/cases/update-step`, `PUT /api/cases/{id}/assign-manager`
- `GET/POST /api/cases/{id}/information-sheet`
- `POST /api/documents/upload`, `GET /api/documents/download/{id}`
- `GET /api/activity/logs`, `GET /api/activity/stats`
- `GET /api/sales/partner-report`, `GET /api/reports/partner-commissions`

## Architecture
- Backend: FastAPI + SQLAlchemy (async) + MySQL/MariaDB
- Frontend: React + TailwindCSS + Shadcn UI
- Uploads: Local filesystem (./uploads)
- MariaDB auto-starts via supervisor + start.sh

## Remaining Backlog
- P0: Complete Stripe payment flow (scaffolded, untested)
- P1: Email notifications via SMTP
- P2: PDF report generation, bulk document upload
- P3: SMS (Twilio), Google Calendar, WhatsApp integration
