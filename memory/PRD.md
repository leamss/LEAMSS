# LEAMSS Immigration Portal - PRD

**Version:** 6.0 (MongoDB) | **Updated:** April 3, 2026 | **Status:** Production Ready

## Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, Client roles. User uploaded a 30-point PRD across 3 phases.

## Architecture
- **Backend:** Python FastAPI + MongoDB (motor async driver)
- **Frontend:** React + TailwindCSS + Shadcn UI
- **Database:** MongoDB (auto-seeds on startup)

## Implemented Features

### Core
- JWT auth, 4 roles (admin, case_manager, partner, client), admin impersonation
- Role-based dashboards, Products & Workflow CRUD, User management
- Sales CRUD, Cases, Documents, Tickets, Notifications, Activity Logs, Analytics, Global Search

### Phase 1 Critical Fixes (COMPLETED)
1. Commission on Amount Received (not fee_amount)
2. Mandatory Rejection Reason for sales (min 5 chars)
3. Ticket Closure Comments required (min 10 chars)
4. Workflow Duplicate Step Prevention (case-insensitive)
5. Sales Report: Service Type, Date, Received, Pending, Rejection Reason columns
6. Record Payment endpoint for partial payments
7. Dashboard stats: Received/Pending breakdown

### Phase 2 Features (COMPLETED)
1. Commission Effective Date — tracked in commission_rate_history with effective_from
2. Client Ticket Routing — auto-routes by category, admin can reassign
3. Refund Module — auto-adjusts commission, full CRUD at /api/refunds
4. Currency Conversion (USD/INR) — configurable exchange rate, dual display toggle
5. Payment Collection Tracker Widget — overdue/due_soon/upcoming color-coded

### P1: Case Manager Document Privileges (COMPLETED)
1. View, approve, reject, revision_required with mandatory comment on rejection/revision (min 5 chars)
2. Batch approve/reject — select multiple docs, bulk action
3. Request additional docs via auto-ticket creation to client
4. Search & filter by query, type, status
5. Uploader name & reviewer comments visible in table + case detail
6. Review dialog with View File download button
7. N+1 queries optimized in documents, sales, cases, reports

## Remaining Backlog

### P1 - High Priority
- CRM & Lead Management (pipeline, source tracking, follow-up reminders)
- Notification System (Email, SMS, WhatsApp alerts, trigger-based)

### P2 - Medium Priority
- PDF Report Generation
- Bulk Document Upload
- Email Notifications via SMTP

### P3 - Future
- AI Document Verification, OCR, AI Chatbot
- Drag-and-drop Workflow Builder
- Mobile Applications
- Marketing (referrals, promo codes)
- SMS (Twilio), Calendar, WhatsApp
- Stripe Payment Gateway
