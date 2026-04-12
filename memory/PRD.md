# LEAMSS Immigration Portal — Product Requirements Document

## Original Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, and Client roles. Multi-step case workflows, document management, ticketing, analytics, and payment processing. 34+ advanced features across Phases 1-8.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI, React Router
- **Backend**: FastAPI (Python), Motor (Async MongoDB)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Payments), Resend (Email - mock mode)

## Implemented Features

### Phase 1-3: Core Platform (ALL VERIFIED)
- Multi-role Auth (Admin, Case Manager, Partner, Client)
- Products CRUD & Workflow Builder
- Sales Management (create, approve/reject, commissions)
- Case Lifecycle Management (steps, deadlines, documents)
- Document Upload & Review, Ticketing, Notifications (SSE), User Management

### Phase 4: Intelligence (ALL VERIFIED)
- Activity Log, Global Search, AI Workflow Builder (GPT-5.2), AI Chat Widget, Analytics

### Phase 5: Communication (ALL VERIFIED)
- Chat System, Email Service (mock), Client Onboarding Wizard

### Phase 6: Operations & Analytics (ALL VERIFIED)
- Bulk Ops, SLA Tracker, Case Transfer, Auto Assignment, Surveys, KB, Appointments, Revenue/CM Analytics

### Phase 7: Productivity & Growth (ALL VERIFIED)
- Timeline, Notes/Tags, Canned Responses, Referrals, Greetings, Funnel/Country/Commission Analytics

### Client Self-Service Portal (ALL VERIFIED)
- My Case Journey (flight-tracker), Message Center (WhatsApp-style), My Profile (edit + password + prefs)

### Phase 8: Pre-Assessment Workflow (NEW — ALL VERIFIED) 
Full business process: Partner → ₹5,100 Payment Link → Client Pays → Partner Submits Docs → Admin Reviews → Approve/Reject → Proposal with Payment → Auto Sale Creation

**Stages**: new → payment_pending → payment_received → documents_submitted → under_review → approved/rejected → proposal_sent → case_created

**Partner Features**: Pre-Assessment Pipeline with create form, payment link generation, document upload, submit to admin, send proposal. Stats bar, search, filter, stage progress indicator.

**Admin Features**: Pre-Assessment Queue with pending review list, approve/reject with reason, client details view, all pre-assessments view with stats.

### Cross-cutting (ALL VERIFIED)
- Multi-Language Toggle (Hindi/English), Stripe Payments, Doc Expiry Tracker, NPS Score, SSE Notifications

## Current Bugs: NONE

## Backlog (Prioritized)
- **P1**: Hindi/English translations for inner page content
- **P2**: Email live dispatch (needs RESEND_API_KEY), PDF Reports, Bulk Upload
- **P3**: SMS (Twilio), Google Calendar, react-i18next, Dark Mode

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Test Reports
- iteration_41: 52/52 backend (all 34 features)
- iteration_42: 19/19 (Client Self-Service Portal)
- iteration_43: 32/32 backend + frontend ALL PASS (Pre-Assessment Workflow Phase 8)
