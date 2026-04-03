# LEAMSS Immigration Portal — PRD

## Original Problem Statement
Build a comprehensive immigration services portal (LEAMSS) with role-based dashboards for Admin, Case Manager, Partner, and Client. The portal handles sales tracking, case management, document processing, ticketing, commission tracking, and payment collection.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Backend**: FastAPI (Python), MongoDB (Motor async driver)
- **Auth**: JWT-based custom authentication

## User Personas
- **Admin**: Full system access, user management, commission config, reports
- **Case Manager**: Case workflows, document review, ticket management
- **Partner**: Sale booking, commission tracking, support tickets
- **Client**: Case status, document upload/download, support tickets, info sheet

## Core Requirements
1. Role-based authentication and dashboards
2. Sales management with multi-currency support (INR base)
3. Case workflow with step-by-step progression
4. Document management with upload/download/review
5. Ticketing system with real-time visibility
6. Commission tracking (global, per-partner, per-product)
7. Analytics dashboard and reporting
8. Activity logging

---

## What's Been Implemented

### Phase 1 — Core Features (DONE)
- [x] JWT auth with 4 roles (admin, case_manager, partner, client)
- [x] Admin Dashboard (users, products, cases, sales, tickets, refunds, analytics, settings)
- [x] Partner Dashboard (sales booking, commissions, support)
- [x] Case Manager Dashboard (case management, document review, batch operations)
- [x] Client Dashboard (case status, documents, tickets, info sheet)
- [x] Global search
- [x] Activity log UI
- [x] N+1 query optimizations

### Phase 1 — Bug Fixes (DONE - April 3, 2026)
- [x] Document download (doc.file_id → doc.id)
- [x] Date formatting (doc.upload_date → doc.uploaded_at)
- [x] Ticket visibility (/my-tickets endpoint, broadened query)
- [x] Ticket field names (created_by_name, created_by_role, user_name, user_role)
- [x] Resolution note validation UX (focus, scroll, clearer messaging)
- [x] Client Information Sheet tab visibility

### Phase 1 — Advanced Features (DONE - April 3, 2026)
- [x] Per-partner per-product custom commission rates (CRUD API + Admin UI)
- [x] INR base currency with multi-currency support (USD, AUD, CAD, GBP, EUR)
- [x] Exchange rate configuration in settings
- [x] Currency selector in Partner sale form
- [x] Auto-conversion to INR at booking time
- [x] ₹ (INR) currency display across all dashboards
- [x] Commission calculation on amount_received (not fee_amount)
- [x] Mandatory ticket closure comments and rejection reasons
- [x] Dual currency toggle (legacy)
- [x] Refunds UI and backend logic
- [x] Payment Collection Tracker widget
- [x] Case Manager Document Privileges (batch approve/reject, mandatory rejection comments)

---

## Prioritized Backlog

### P1 — In Progress / Next
- [ ] CRM & Lead Management (lead pipeline, source tracking, follow-up reminders)
- [ ] Notification System (email/SMS/WhatsApp alerts for key events)
- [ ] Email service integration (currently scaffolded but not triggered)

### P2 — Planned
- [ ] PDF Report Generation (export sales, cases, commissions)
- [ ] Bulk Document Upload
- [ ] AI Document Verification / OCR
- [ ] Activity log injection into business logic (create sale, update case, approve document)
- [ ] Stripe Payment Gateway integration

### P3 — Future
- [ ] Drag-and-drop Workflow Builder
- [ ] Mobile Applications (client + staff)
- [ ] Marketing Features (referral system, promo codes)
- [ ] SMS Notifications via Twilio
- [ ] Google Calendar integration for deadlines
- [ ] AI Chatbot for client queries

---

## Key API Endpoints
- `POST /api/auth/login` — JWT login
- `GET /api/sales`, `POST /api/sales` — Sales CRUD (supports currency field)
- `GET /api/cases/my-cases` — Client cases
- `GET /api/documents/case/{case_id}` — Case documents
- `GET /api/documents/download/{file_id}` — File download
- `GET /api/tickets/my-tickets` — User's tickets (created + targeted)
- `POST /api/partner-commissions` — Set custom commission
- `GET /api/partner-commissions/resolve/{partner_id}/{product_id}` — Resolve effective rate
- `GET /api/settings/exchange-rate` — Multi-currency rates
- `GET /api/analytics/dashboard` — Analytics data
- `GET /api/search` — Global search

## Database Collections (MongoDB)
- `users`, `products`, `workflow_steps`, `sales`, `cases`, `case_steps`
- `documents`, `tickets`, `ticket_messages`, `notifications`
- `audit_logs`, `refunds`, `settings`, `partner_product_commissions`
