# LEAMSS Immigration Portal — Product Requirements Document

## Original Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, and Client roles. Multi-step case workflows, document management, ticketing, analytics, and payment processing. 34+ advanced features across Phases 1-10.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI, React Router
- **Backend**: FastAPI (Python), Motor (Async MongoDB)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Payments), Resend (Email - mock mode)

## Implemented Features

### Phase 1-7: Core Platform (34 features — ALL VERIFIED)
- Multi-role Auth, Products CRUD, Sales, Cases, Documents, Tickets, Notifications, Users
- Activity Log, Global Search, AI Workflow, AI Chat, Analytics
- Chat, Email, Onboarding Wizard
- Bulk Ops, SLA Tracker, Transfers, Auto-Assign, Surveys, KB, Appointments, Revenue/CM Analytics
- Timeline, Notes/Tags, Canned Responses, Referrals, Greetings, Funnel/Country/Commission Analytics

### Client Self-Service Portal (ALL VERIFIED)
- My Case Journey (flight-tracker), Message Center (WhatsApp-style), My Profile (edit + password + prefs)

### Phase 8: Pre-Assessment Workflow (ALL VERIFIED)
Full flow: Partner → ₹5,100 Payment Link → Client Pays → Partner Submits Docs → Admin Reviews → Approve/Reject → Proposal + Payment → Sale Auto-Created
- Partner: Pre-Assessment Pipeline (create, send payment, upload docs, submit, send proposal)
- Admin: Pre-Assessment Queue (review, approve/reject)

### Phase 9: Partner Power Tools (ALL VERIFIED)
- **Lead Pipeline Kanban Board**: Visual 6-column board (New Leads → Payment Pending → Paid → Under Review → Approved → Proposal Sent) with lead cards
- **Partner Performance Dashboard**: Monthly Targets with progress bars (Sales, Revenue, Leads, Commission), Key Metrics (Revenue, Approval Rate, Deal Size, Lead Conversion), Revenue Trend chart (6 months), Top Products, Top Countries with progress bars
- **Partner Leaderboard**: Ranked table with sales, revenue, commission, leads, "You" badge highlight

### Phase 10: Admin Superpowers (NEW — ALL VERIFIED, 100% Pass Rate)
- **10A: Unified Approval Center**: Centralized view of ALL pending items (Sales, Pre-Assessments, Documents, Urgent Tickets). Summary cards with counts. Search & type filter. Quick approve/reject with notes dialog.
- **10B: Refund Manager Enhanced**: Complete refund management with stats dashboard. 3 tabs: Refund History (searchable table), PA Refunds Pending (process rejected pre-assessment refunds), Issue New Refund (from eligible sales). Monthly refund trend tracking.
- **10C: Revenue Dashboard Enhanced**: Top stats (Total Revenue, Collected with %, Commission, Net Revenue). Monthly revenue trend bar chart. 3 breakdowns: By Partner, By Service/Product, By Payment Method. PA revenue included.
- **10D: Custom Report Builder**: 6 pre-built templates (Revenue Summary, Partner Performance, Case Status, Client Directory, Pre-Assessment Pipeline, Refund Report). Custom filters (date range, partner, product, status). Data table with CSV download and Print/PDF export.

### Cross-cutting (ALL VERIFIED)
- Multi-Language Toggle (Hindi/English), Stripe Payments, Doc Expiry, NPS, SSE Notifications

## Current Bugs: NONE

## Backlog (Prioritized)
- **P1**: Phase 11 — Case Manager Efficiency (Smart Workload View, Client Communication Hub, Batch Case Operations)
- **P1**: Phase 12 — Client Experience Enhancement (Self-Eligibility Checker, EMI Payment Plans, Family Member Management, Smart Document Upload)
- **P2**: Hindi/English deep i18n translations, PDF Reports, Bulk Upload
- **P3**: Phase 13 — Cross-Platform (WhatsApp via Twilio, Dark Mode, PWA, Weekly Email Digest)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Architecture
```
/app
├── backend/
│   ├── core/           # database.py, auth.py, email_service.py, services.py
│   ├── routers/        # 26+ routers including admin_superpowers.py
│   ├── tests/          # test_all_34_features.py, test_phase10_admin_superpowers.py
│   └── server.py       # FastAPI main entry
├── frontend/
│   ├── src/
│   │   ├── components/ # ApprovalCenter, RefundManager, RevenueDashboard, ReportBuilder + 20 more
│   │   ├── pages/      # AdminDashboard, PartnerDashboard, CaseManagerDashboard, ClientDashboard + 16 more
│   │   └── App.js
└── memory/             # PRD.md, test_credentials.md
```
