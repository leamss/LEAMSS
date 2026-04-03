# LEAMSS Immigration Portal - PRD

**Version:** 4.0 (MongoDB) | **Updated:** April 3, 2026 | **Status:** Production Ready

## Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, Client roles.
User uploaded a 30-point PRD across 3 phases. Phase 1 (Critical Fixes) is now complete.

## Architecture
- **Backend:** Python FastAPI + MongoDB (motor async driver)
- **Frontend:** React + TailwindCSS + Shadcn UI  
- **Database:** MongoDB (native to environment, auto-seeds on startup)
- **Uploads:** Local filesystem (./uploads)

## Implemented Features

### Authentication & Roles
- JWT auth, 4 roles, admin impersonation, password change

### Admin Dashboard
- Stats with Received/Pending breakdown, Sales with filter (All/Pending/Approved/Rejected)
- 2-step sale approval, Client credentials dialog with Copy/Email/WhatsApp sharing
- Products & Workflow CRUD (with duplicate prevention), User management
- Commission reports (calculated on amount received), Activity Log, Analytics, Settings
- Rejection reason dialog (mandatory when rejecting sales)
- Sales Report table with Service Type, Date, Received, Pending, Rejection Reason columns

### Case Manager Dashboard
- My Cases, workflow step updates, document review
- Information Sheet, Additional document requests, tickets

### Partner Dashboard
- Create sales with all payment methods, document upload
- Commission tracking (% of received amount), Amt Received column in table

### Client Dashboard
- Case progress, document uploads, tickets

### Cross-cutting
- Activity logging, notifications, ticketing (with closure comments), global search, analytics

## Phase 1 Critical Fixes (COMPLETED - April 3, 2026)
1. Commission on Amount Received (not fee_amount) - DONE
2. Mandatory Rejection Reason for sales (min 5 chars) - DONE
3. Ticket Closure Comments required (min 10 chars) - DONE
4. Workflow Duplicate Step Prevention (case-insensitive) - DONE
5. Sales Report: Service Type, Date, Received, Pending, Rejection Reason - DONE
6. Record Payment endpoint for partial payments - DONE
7. Dashboard stats: Received/Pending breakdown - DONE

## Remaining Backlog

### Phase 1 Continued (P1-P2)
- P2: Currency Conversion (USD to INR) across all modules
- P2: Refund Module with automatic commission adjustment
- P1: Commission effective date (apply rate changes forward, not retroactively)
- P1: Client Portal Ticket Routing (assign to Admin/CM, auto-routing)
- P1: Case Manager Document Privileges (view, approve, reject, request via ticket/email, filters)

### Phase 2 (Core Features)
- P1: CRM & Lead Management (pipeline, source tracking, follow-up reminders)
- P1: Notification System (Email, SMS, WhatsApp alerts, trigger-based)
- P1: Email Notifications via SMTP
- P2: PDF Report Generation
- P2: Bulk Document Upload

### Phase 3 (Advanced)
- P2: AI Document Verification, OCR-based extraction, AI Chatbot
- P2: Drag-and-drop Workflow Builder
- P3: Mobile Applications (Client & Staff)
- P3: Marketing (referral system, promo codes)
- P3: SMS (Twilio), Calendar, WhatsApp
- P3: Stripe Payment Gateway
