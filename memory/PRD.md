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
│   ├── routers/        # activity.py, ai_workflow_builder.py, ai_intelligence.py, cases.py, documents.py, etc.
│   ├── uploads/        # receipts/, reports/, leamss-logo.png
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ # DashboardShell.jsx, InfoSheetEditor.jsx, StatCard.jsx, AIChatWidget.jsx
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

## Key API Endpoints
- Auth: `POST /api/auth/login`
- Activity: `GET /api/activity/logs`, `/live-feed`, `/stats`, `/case/{id}`, `/user/{id}`
- AI Workflow: `GET /api/ai-workflow/countries`, `/templates`, `POST /generate`, `POST /save`
- Cases: `GET /api/cases/info-sheet-schema`, `GET/POST /api/cases/{id}/info-sheet`
- Documents: `POST /api/documents/set-expiry`, `GET /api/documents/check-reminders`
- Reports: `GET /api/reports/export/info-sheet/{case_id}`

## Prioritized Backlog (34 Enhancement Items)
### Implemented (Phase 4):
- #17 AI Workflow Builder - DONE
- #18 AI Document Requirement Mapper - DONE (integrated in workflow builder)
- #21-25 Real-Time Activity Log System - DONE
- #26 Email Notifications (Resend) - DONE (needs API key for real emails)

### Next Up (Phase 5):
- #2 Real-Time In-App Chat (Client <-> Case Manager)
- #1 Client Onboarding Wizard
- #4 Smart Document Checklist
- #5 Automated Milestone Notifications
- #9 Smart Workload Dashboard for Case Manager
- #11 Auto Case Assignment

### Future Phases:
- #3 Case Timeline View, #6 Satisfaction Survey, #7 Multi-Language
- #8 Knowledge Base, #10 Bulk Operations, #12 SLA/Deadline Tracking
- #13 Quick Notes & Tags, #14 Case Transfer, #15 Document Annotation
- #16 Canned Responses, #19 AI Case Risk Assessment, #20 AI Document Validator
- #27 Appointment Scheduling, #28 Referral Program, #29 Client Greetings
- #30 Revenue Forecasting, #31 CM Performance Metrics, #32 Conversion Funnel
- #33 Country/Product Analytics, #34 Commission Analytics

## Test Results
- Iteration 37: 100% pass (17/17 backend + all frontend verified) - Activity Log, AI Workflow Builder, Email Service
- Iteration 36: 100% pass - DashboardShell, Sidebar Navigation, P0 Info Sheets
- Iterations 30-35: All passed

## Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
