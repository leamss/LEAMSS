# LEAMSS Immigration Portal — Product Requirements Document

## Original Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, and Client roles. Multi-step case workflows, document management, ticketing, analytics, and payment processing. 34+ advanced features across Phases 1-12.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI, React Router
- **Backend**: FastAPI (Python), Motor (Async MongoDB)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Payments), Resend (Email - mock mode)

## Implemented Features

### Phase 1-7: Core Platform (34 features — ALL VERIFIED)
- Multi-role Auth, Products CRUD, Sales, Cases, Documents, Tickets, Notifications, Users
- Activity Log, Global Search, AI Workflow, AI Chat, Analytics, Chat, Email, Onboarding Wizard
- Bulk Ops, SLA Tracker, Transfers, Auto-Assign, Surveys, KB, Appointments, Revenue/CM Analytics
- Timeline, Notes/Tags, Canned Responses, Referrals, Greetings, Funnel/Country/Commission Analytics

### Client Self-Service Portal (ALL VERIFIED)
- My Case Journey, Message Center, My Profile

### Phase 8: Pre-Assessment Workflow (ALL VERIFIED)
- Partner → ₹5,100 Payment → Client Pays → Docs → Admin Review → Approve/Reject → Proposal → Sale

### Phase 9: Partner Power Tools (ALL VERIFIED)
- Lead Pipeline Kanban, Partner Performance Dashboard, Partner Leaderboard

### Phase 10: Admin Superpowers (ALL VERIFIED)
- Unified Approval Center, Refund Manager Enhanced, Revenue Dashboard Enhanced, Custom Report Builder

### Email Digest (ALL VERIFIED)
- Admin weekly stats summary (Revenue, Approvals, Cases, Tickets, Top Partner), Preview, Send Now, Frequency control

### Phase 11: Case Manager Efficiency (ALL VERIFIED)
- Smart Workload View (prioritized cases with score), Client Communication Hub, Batch Case Operations

### Phase 12: Client Experience Enhancement (NEW — ALL VERIFIED — 100% Pass)
- **12A: Self-Eligibility Checker**: Score-based assessment for 4 programs (Canada PR, Australia PR, Student Visa, Work Permit) with tips. Public + authenticated endpoints.
- **12B: EMI Payment Plans**: Admin creates installment plans (3/6/12 months), Client sees schedule with pay buttons, progress tracking.
- **12C: Family Member Management**: Full CRUD for family members (spouse/child/parent/sibling), include in application toggle, passport & DOB tracking.
- **12D: Document Completion Tracker**: Overall completion %, per-step breakdown, required vs uploaded vs verified counts, document status chips.

### Cross-cutting (ALL VERIFIED)
- Multi-Language Toggle (Hindi/English), Stripe Payments, Doc Expiry, NPS, SSE Notifications

## Current Bugs: NONE

## Backlog (Prioritized)
- **P2**: Hindi/English deep i18n translations, PDF Reports, Bulk Upload
- **P3**: Phase 13 — Cross-Platform (WhatsApp via Twilio, Dark Mode, PWA, Weekly Email Digest live)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Architecture
```
/app/backend/routers/ — 30+ routers
/app/frontend/src/components/ — 30+ components
/app/frontend/src/pages/ — 20+ pages
```
