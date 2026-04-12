# LEAMSS Immigration Portal — Product Requirements Document

## Original Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, and Client roles. Multi-step case workflows, document management, ticketing, analytics, and payment processing. 34+ advanced features across Phases 1-11.

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

### Phase 9: Partner Power Tools (ALL VERIFIED)
- Lead Pipeline Kanban Board, Partner Performance Dashboard, Partner Leaderboard

### Phase 10: Admin Superpowers (ALL VERIFIED — 100% Pass)
- **10A: Unified Approval Center**: Centralized pending items (Sales, PA, Documents, Tickets) with approve/reject
- **10B: Refund Manager Enhanced**: 3-tab refund management (History, PA Pending, Issue New)
- **10C: Revenue Dashboard Enhanced**: Monthly trend chart, partner/product/payment breakdowns
- **10D: Custom Report Builder**: 6 templates + custom filters + CSV/PDF export

### Email Digest (NEW — ALL VERIFIED)
- Admin weekly stats summary email (Revenue, Approvals, Cases, Tickets, Top Partner)
- Preview, Send Now, Frequency settings (daily/weekly/monthly)
- Works in mock mode until RESEND_API_KEY is configured

### Phase 11: Case Manager Efficiency (NEW — ALL VERIFIED — 100% Pass)
- **11A: Smart Workload View**: Prioritized case view (Overdue → Due Today → Action Needed → Upcoming → On Track) with workload score
- **11B: Client Communication Hub**: Direct CM-to-client messaging, quick templates (Doc Reminder, Step Complete, Payment, Info Request), message types, read/unread tracking
- **11C: Batch Case Operations**: Multi-select cases + batch actions (Add Note, Notify Clients, Request Docs, Change Status)

### Cross-cutting (ALL VERIFIED)
- Multi-Language Toggle (Hindi/English), Stripe Payments, Doc Expiry, NPS, SSE Notifications

## Current Bugs: NONE

## Backlog (Prioritized)
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
│   ├── routers/        # 28+ routers including admin_superpowers, email_digest, cm_efficiency
│   ├── tests/          # test_phase10, test_phase11 + more
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ # ApprovalCenter, RefundManager, RevenueDashboard, ReportBuilder, EmailDigest, SmartWorkload, CommunicationHub, BatchCaseOps + 20 more
│   │   ├── pages/      # AdminDashboard, PartnerDashboard, CaseManagerDashboard, ClientDashboard + 16 more
│   │   └── App.js
└── memory/             # PRD.md, test_credentials.md
```
