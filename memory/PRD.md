# LEAMSS Immigration Portal — PRD

## Original Problem Statement
Build a comprehensive immigration services portal (LEAMSS) with role-based dashboards for Admin, Case Manager, Partner, and Client. The portal handles sales tracking, case management, document processing, ticketing, commission tracking, and payment collection.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Backend**: FastAPI (Python), MongoDB (Motor async driver)
- **Auth**: JWT-based custom authentication
- **AI**: GPT-5.2 via emergentintegrations (Universal Key)
- **PDF**: reportlab for server-side PDF generation

## User Personas
- **Admin**: Full system access, user management (with password reset), commission config, reports, analytics, workflow builder, marketing
- **Case Manager**: Case workflows, document review, ticket management, info sheets (request/edit), AI document verification
- **Partner**: Sale booking (multi-currency), commission tracking, support tickets, referral codes
- **Client**: Case status, document upload/download, support tickets, info sheet view/edit

## What's Been Implemented

### Phase 1 — Core Features (DONE)
- [x] JWT auth with 4 roles
- [x] All 4 role-based dashboards
- [x] Sales, Cases, Documents, Tickets, Commissions, Refunds
- [x] Global search, Activity log

### Phase 1 — Bug Fixes (DONE — April 3)
- [x] Document download, Date formatting, Ticket visibility, Client Info Sheet
- [x] Analytics syncing, Sale currency display (INR base)
- [x] Per-partner per-product custom commission rates

### Phase A-D — Features (DONE — April 4)
- [x] Workflow Builder, Marketing Dashboard, PDF Reports, AI Document Verification
- [x] Activity Log injection, Notification system (mocked)
- [x] Mobile responsiveness (hamburger sidebar on Admin/Partner/CaseManager)
- [x] Email Service (MOCKED — logs to DB)

### Bug Fixes & Features (DONE — April 4, Session 2)
- [x] **BUG FIX**: Sale document download — added `/api/sales/document/download/{file_id}` endpoint
- [x] **BUG FIX**: "Request Additional Document" 405 error — fixed endpoint URL and made `step_order` optional
- [x] **BUG FIX**: Commission % not reflecting from products — added product `commission_rate` to resolution chain (explicit > custom > product > partner default)
- [x] **FEATURE**: Admin can edit user profiles + reset passwords via enhanced User Dialog
- [x] **FEATURE**: Information Sheet enhanced — dependents section, case manager notes, change history tracking, "Request Info Update" button
- [x] **UI REDESIGN**: Pending Reviews grouped by client (expandable accordion with badge counts)
- [x] **UI REDESIGN**: All Documents grouped by client (expandable + search/filter bar + batch actions)
- [x] **FIX**: Invalid Date display for null dates in document requests
- [x] All 21 backend tests + all frontend tests passing (iteration 25)

---

### Marketing Hub (DONE — Dec 2025)
- [x] **CRM Lead Management**: Full pipeline (new → contacted → qualified → proposal → negotiation → won/lost), notes, follow-ups, source tracking
- [x] **Email Campaigns**: Create, send (MOCKED to DB), track recipients, campaign stats
- [x] **Service Calculator**: Public eligibility assessment tool — scores users against products, "Enquire Now" flow to Lead Capture
- [x] **Lead Capture**: Public inquiry form with URL prefill from Calculator, thank-you confirmation
- [x] **Testimonials**: Admin CRUD for client success stories with ratings, featured flag
- [x] **Partner Leaderboard**: Rankings by revenue, sales count, conversion rate, tier system (gold/silver/bronze)
- [x] **Promo Codes**: Create/manage discount codes (percentage or flat)
- [x] All 23 marketing API tests passing (iteration 26)

### Sales Enhancement — Promo Code, Discount & Assignment Flow (DONE — Dec 2025)
- [x] **Promo Code Integration**: Partners can apply promo codes during sale creation; auto-validates, calculates discount, increments usage
- [x] **Additional Discount**: Partners can offer extra % discount to clients (needs admin approval as part of sale approval)
- [x] **Price Breakdown**: Live preview showing Original Fee → Promo Discount → Additional Discount → Final Fee in Partner's New Sale form
- [x] **Client Proposal**: Automated proposal email sent to client on sale creation with discount details
- [x] **Modified Approval Flow**: Admin approves sale → Case created WITHOUT case manager → Case status = "pending_assignment"
- [x] **Pending Assignment Tab**: Dedicated Admin sidebar tab showing unassigned cases with badge count, fee info, payment status, and "Select Manager" dropdown
- [x] **Manager Assignment**: Admin assigns case manager from Pending Assignment tab → Case status changes to "active", manager gets notified
- [x] **Discount Badges**: Both Admin & Partner sales views show promo/discount/savings badges
- [x] All 11 promo/discount/assignment tests passing (iteration 27)

### Client Payment Portal with Stripe (DONE — Dec 2025)
- [x] **Stripe Integration**: Emergent Stripe checkout with INR payments
- [x] **Client Proposals View**: Clients see all their sales with full price breakdown (original fee, promo, additional discount, final fee)
- [x] **Online Payments**: "Pay Now" button initiates Stripe checkout for pending amounts
- [x] **Payment Status Polling**: Payment success page polls Stripe and updates sale automatically
- [x] **Payment History**: Transaction history with dates and amounts
- [x] **Webhook Support**: Stripe webhook endpoint for server-side payment confirmation
- [x] **Idempotent Processing**: Same payment won't be processed twice
- [x] **Commission Auto-Update**: Commission recalculated after each payment
- [x] All 12 Stripe payment tests passing (iteration 28)

---

## Prioritized Backlog

### P1 — Next
- [ ] Real email service integration (SendGrid/Resend — replace mock)
- [ ] AI Chatbot for client queries

### P2 — Planned
- [ ] AI Chatbot for client queries
- [ ] Bulk Document Upload UI improvements
- [ ] PDF report download improvements

### P3 — Future
- [ ] SMS Notifications (Twilio)
- [ ] Google Calendar integration
- [ ] Standalone mobile apps

---

## Payment API Endpoints
- `GET /api/payments/my-proposals` — Client's sales with price breakdown
- `POST /api/payments/create-checkout` — Initiate Stripe checkout
- `GET /api/payments/status/{session_id}` — Poll payment status
- `GET /api/payments/history/{sale_id}` — Transaction history
- `POST /api/webhook/stripe` — Stripe webhook

## Key API Endpoints
- `POST /api/auth/login` — JWT login
- `GET/POST /api/sales` — Sales CRUD
- `GET /api/sales/document/download/{file_id}` — Download sale attachment
- `PUT /api/users/{id}/reset-password` — Admin password reset
- `POST /api/cases/request-document` — Request additional document (null step_order OK)
- `POST /api/cases/{id}/request-info-sheet` — Request client info sheet update
- `POST /api/cases/{id}/information-sheet` — Save info sheet with change tracking
- `GET /api/workflows/{product_id}` — Workflow steps
- `POST /api/marketing/promo` — Promo codes
- `GET /api/reports/export/sales-report` — PDF report
- `POST /api/ai/verify-document/{doc_id}` — AI verification
- `GET /api/activity/logs` — Activity audit logs
- `GET /api/activity/email-logs` — Email logs (admin)

## Database Collections
`users`, `products`, `workflow_steps`, `sales`, `sale_documents`, `cases`, `case_steps`, `documents`, `tickets`, `ticket_messages`, `notifications`, `audit_logs`, `refunds`, `settings`, `partner_product_commissions`, `referrals`, `promo_codes`, `email_logs`, `information_sheets`, `additional_doc_requests`, `leads`, `follow_ups`, `campaigns`, `campaign_recipients`, `testimonials`, `cross_sell_recommendations`
