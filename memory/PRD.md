# LEAMSS Immigration Portal - Product Requirements Document

## Original Problem Statement
Build a comprehensive LEAMSS Portal for an immigration service supporting Admin, Case Manager, Partner, and Client roles. Features include multi-role dashboards, workflow automation, CRM tools, document management, AI intelligence, and payment processing.

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Lucide React Icons
- **Backend**: FastAPI, Motor (MongoDB async driver)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (via emergentintegrations), Stripe Payments

## Core Architecture
```
/app
├── backend/
│   ├── core/           # database.py, auth.py, models.py
│   ├── routers/        # ai_intelligence.py, cases.py, documents.py, pdf_reports.py, etc.
│   ├── uploads/        # receipts/, reports/, leamss-logo.png
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ # DashboardShell.jsx, InfoSheetEditor.jsx, StatCard.jsx, AIChatWidget.jsx, NotificationBell.jsx
│   │   ├── pages/      # AdminDashboard.jsx, CaseManagerDashboard.jsx, ClientDashboard.jsx, PartnerDashboard.jsx
│   │   └── App.js
└── memory/             # PRD.md, test_credentials.md
```

## User Roles & Access
- **Admin**: Full control - Sales management, user management, case assignment, products, tickets, settings, analytics
- **Case Manager**: Case workflows, document review, info sheet editing, expiry tracking
- **Partner**: Sales submission, commission tracking, ticket support
- **Client**: Case overview, document upload, info sheet, payments, workflow steps, AI chat

## Implemented Features (Completed)

### Phase 1 - Core Portal (Done)
- Multi-role authentication (JWT)
- Role-based dashboards
- Case workflow enforcement with step locking
- Document upload, review, and approval
- Ticketing system

### Phase 2 - Advanced Features (Done)
- LEAMSS Logo integration across UI and all PDF Reports
- Bulk Document Upload with Drag-and-Drop
- Document Expiry Tracking with Dashboard Widgets
- Auto In-App Reminders for Expiring Documents
- Information Sheet Editor (dynamic schema, unlimited repeatable entries)
- OCR Resume parsing to auto-fill Info Sheet
- AI Chatbot with case/step/document context
- Info Sheet PDF Export Generation
- Stripe Payment Portal for clients

### Phase 3 - UI/UX Overhaul (Done - Dec 2025)
- **Shared DashboardShell component** with grouped collapsible sidebar navigation
- **Admin sidebar groups**: Sales & Finance, Cases & Users, System, Tools
- **Case Manager sidebar groups**: Case Management (My Cases, Pending Review, Info Sheets), Documents (All Documents, Expiry Alerts)
- **Client sidebar groups**: My Case (Action Required, Workflow Steps, My Documents, My Info Sheet), Finance (Payments)
- **Partner sidebar**: Dashboard, My Sales, Commission, Support
- **P0: Case Manager Info Sheet View/Edit** - New "Info Sheets" tab showing all client cases, clicking opens InfoSheetEditor
- Consistent teal #2a777a brand theme across all portals
- Mobile-responsive sidebar with toggle button
- AdminReturnBanner moved to shared DashboardShell
- StatCard shared component for dashboard metrics

## Key API Endpoints
- `POST /api/auth/login` - Authentication
- `GET /api/cases/info-sheet-schema` - Info sheet schema
- `GET /api/cases/{case_id}/info-sheet` - Get info sheet data
- `POST /api/cases/{case_id}/info-sheet` - Save info sheet data
- `POST /api/documents/set-expiry` - Set document expiry
- `GET /api/documents/check-reminders` - Check expiry reminders
- `GET /api/reports/export/info-sheet/{case_id}` - Export info sheet PDF

## Prioritized Backlog
- P1: Real Email Service Integration (SendGrid/Resend) for Expiry Reminders (currently MOCKED as in-app notifications)
- P2: PDF Report enhancements
- P2: Bulk document upload improvements
- P3: SMS Notifications via Twilio
- P3: Google Calendar Integration for deadlines
- P3: Bulk case operations for Admin

## Test Results
- Iteration 36: 100% pass rate - All 4 dashboards, sidebar navigation, P0 Info Sheets, mobile responsive, logout
- Previous: Iterations 30-35 all passed

## Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
