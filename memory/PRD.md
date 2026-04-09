# LEAMSS Immigration Portal - Product Requirements Document

## Original Problem Statement
Build a comprehensive LEAMSS Portal for an immigration service supporting Admin, Case Manager, Partner, and Client roles. Features include multi-role dashboards, workflow automation, CRM tools, document management, AI intelligence, and payment processing. The goal is to become the world's best immigration company built on honesty and transparency.

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Lucide React Icons
- **Backend**: FastAPI, Motor (MongoDB async driver)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (via emergentintegrations), Stripe Payments, Resend Email (configured but needs API key)

## Core Architecture
```
/app
├── backend/
│   ├── core/           # database.py, auth.py, models.py, services.py, email_service.py
│   ├── routers/        # chat.py, ai_workflow_builder.py, ai_intelligence.py, cases.py, activity.py, etc.
│   ├── uploads/        # receipts/, reports/, leamss-logo.png
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ # DashboardShell.jsx, ChatWidget.jsx, OnboardingWizard.jsx, DocumentChecklist.jsx, WorkloadDashboard.jsx, InfoSheetEditor.jsx, AIChatWidget.jsx
│   │   ├── pages/      # AdminDashboard.jsx, CaseManagerDashboard.jsx, ClientDashboard.jsx, PartnerDashboard.jsx, ActivityLog.jsx, AIWorkflowBuilder.jsx
│   │   └── App.js
└── memory/             # PRD.md, test_credentials.md
```

## Implemented Features

### Phase 1 - Core Portal (Done)
- Multi-role JWT authentication
- Role-based dashboards (Admin, Case Manager, Partner, Client)
- Case workflow enforcement with step locking
- Document upload, review, and approval
- Ticketing system

### Phase 2 - Advanced Features (Done)
- LEAMSS Logo across UI and PDF Reports
- Bulk Document Upload with Drag-and-Drop
- Document Expiry Tracking with Auto In-App Reminders
- Information Sheet Editor (dynamic schema, unlimited repeatable entries, OCR resume parsing)
- AI Chatbot with case/step/document context
- Info Sheet PDF Export
- Stripe Payment Portal

### Phase 3 - UI/UX Overhaul (Done - Dec 2025)
- Shared DashboardShell component with grouped collapsible sidebar
- Admin: Sales & Finance, Cases & Users, System, Tools groups
- Case Manager: Case Management (with Info Sheets P0), Documents groups
- Client: My Case, Finance groups
- Partner: Clean flat navigation
- P0: Case Manager Info Sheet View/Edit feature

### Phase 4 - Intelligence & Monitoring (Done - Dec 2025)
- **Comprehensive Activity Log System**: Live feed, By User view, By Type view, stats cards, filters (time period, entity type), per-case/per-user drill-down, 940+ activities tracked
- **AI Workflow Builder**: 10 quick templates (Canada PR, Australia PR, Tourist visas for 7 countries, UAE Golden Visa), custom country/service selection, GPT-5.2 generates complete workflows with steps, documents per step, success tips, rejection reasons. Admin can edit and save as product.
- **Email Service**: Resend integration with HTML templates for case updates, document reminders, payment confirmations, welcome emails, ticket updates. Graceful fallback to in-app mock when no API key.

### Phase 5 - Communication & Productivity (Done - Dec 2025)
- **Real-Time In-App Chat**: Client <-> Case Manager messaging with floating chat widget, conversation management, unread counts, read receipts, notification triggers
- **Client Onboarding Wizard**: 5-step guided onboarding (Welcome, Profile Check, Info Sheet, Documents, AI Tips), skip & remember, case-aware
- **Smart Document Checklist**: Step-wise document progress tracking, per-step required docs, approval status, overall completion percentage
- **Smart Workload Dashboard**: Case Manager productivity view with active cases, pending reviews, expiring docs, priority task list, case distribution

## Key API Endpoints
- Auth: `POST /api/auth/login`
- Activity: `GET /api/activity/logs`, `/live-feed`, `/stats`, `/case/{id}`, `/user/{id}`
- AI Workflow: `GET /api/ai-workflow/countries`, `/templates`, `POST /generate`, `POST /save`
- Cases: `GET /api/cases/info-sheet-schema`, `GET/POST /api/cases/{id}/info-sheet`, `GET /api/cases/workload/summary`
- Chat: `GET/POST /api/chat/conversations`, `GET /api/chat/messages/{id}`, `POST /api/chat/messages`, `GET /api/chat/unread-count`
- Documents: `POST /api/documents/set-expiry`, `GET /api/documents/check-reminders`
- Reports: `GET /api/reports/export/info-sheet/{case_id}`

## Prioritized Backlog (34 Enhancement Items)
### Implemented:
- #2 Real-Time In-App Chat (Client <-> Case Manager) - DONE (Phase 5)
- #1 Client Onboarding Wizard - DONE (Phase 5)
- #4 Smart Document Checklist - DONE (Phase 5)
- #9 Smart Workload Dashboard for Case Manager - DONE (Phase 5)
- #17 AI Workflow Builder - DONE (Phase 4)
- #18 AI Document Requirement Mapper - DONE (Phase 4)
- #21-25 Real-Time Activity Log System - DONE (Phase 4)
- #26 Email Notifications (Resend) - DONE (Phase 4, needs API key for real emails)

### Next Up (Phase 6 - Scale Up):
- #10 Bulk Operations (Approve multiple docs/advance multiple cases)
- #12 SLA/Deadline Tracking per Step with Alerts
- #11 Auto Case Assignment based on workload/language
- #14 Case Transfer & Document Annotation

### Future Phases:
- #3 Case Timeline View, #6 Satisfaction Survey, #7 Multi-Language
- #8 Knowledge Base, #13 Quick Notes & Tags, #15 Document Annotation
- #16 Canned Responses, #19 AI Case Risk Assessment, #20 AI Document Validator
- #27 Appointment Scheduling, #28 Referral Program, #29 Client Greetings
- #30 Revenue Forecasting, #31 CM Performance Metrics, #32 Conversion Funnel
- #33 Country/Product Analytics, #34 Commission Analytics

## Test Results
- Iteration 38: 100% pass (20/20 backend + all frontend) - Phase 5: Chat, Onboarding, Checklist, Workload
- Iteration 37: 100% pass (17/17 backend + all frontend) - Phase 4: Activity Log, AI Workflow Builder, Email Service
- Iteration 36: 100% pass - DashboardShell, Sidebar Navigation, P0 Info Sheets

## Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
