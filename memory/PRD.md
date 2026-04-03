# LEAMSS Immigration Portal - PRD

**Version:** 5.0 (MongoDB) | **Updated:** April 3, 2026 | **Status:** Production Ready

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

### Phase 1 Critical Fixes (COMPLETED - April 3, 2026)
1. Commission on Amount Received (not fee_amount)
2. Mandatory Rejection Reason for sales (min 5 chars) with dialog
3. Ticket Closure Comments required (min 10 chars)
4. Workflow Duplicate Step Prevention (case-insensitive)
5. Sales Report: Service Type, Date, Received, Pending, Rejection Reason columns
6. Record Payment endpoint for partial payments
7. Dashboard stats: Received/Pending breakdown

### Phase 2 Features (COMPLETED - April 3, 2026)
1. **Commission Effective Date** - Rate changes tracked in `commission_rate_history` array with `effective_from` date
2. **Client Ticket Routing** - Auto-routes by category (document/payment → case_manager, general → admin). Admin can reassign tickets.
3. **Refund Module** - Full CRUD at `/api/refunds`. Auto-adjusts commission when refund processed. Validates reason/amount.
4. **Currency Conversion (USD ↔ INR)** - Configurable exchange rate in settings. Dual currency display toggle on dashboard.
5. **Payment Collection Tracker Widget** - Dashboard widget showing overdue (red), due this week (amber), upcoming (green) payment deadlines.

## Remaining Backlog

### P1 - High Priority
- CRM & Lead Management (pipeline, source tracking, follow-up reminders)
- Notification System (Email, SMS, WhatsApp alerts, trigger-based)
- Case Manager Document Privileges (view, approve, reject, request via ticket/email, filters)

### P2 - Medium Priority
- PDF Report Generation (wire export router to frontend)
- Bulk Document Upload
- Email Notifications via SMTP

### P3 - Future
- AI Document Verification, OCR-based extraction, AI Chatbot
- Drag-and-drop Workflow Builder
- Mobile Applications (Client & Staff)
- Marketing (referral system, promo codes)
- SMS (Twilio), Calendar, WhatsApp
- Stripe Payment Gateway
