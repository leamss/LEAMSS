# LEAMSS Immigration Portal - Product Requirements Document

## Original Problem Statement
Build a comprehensive LEAMSS Portal for an immigration service supporting Admin, Case Manager, Partner, and Client roles. Features include multi-role dashboards, workflow automation, CRM tools, document management, AI intelligence, and payment processing.

## Tech Stack
- **Frontend**: React 18, TailwindCSS, Shadcn UI, Lucide React Icons
- **Backend**: FastAPI, Motor (MongoDB async driver)
- **Database**: MongoDB
- **Integrations**: OpenAI GPT-5.2 (via emergentintegrations), Stripe Payments, Resend Email

## Core Architecture
```
/app
├── backend/
│   ├── core/           # database.py, auth.py, models.py, services.py, email_service.py
│   ├── routers/        # 20+ routers (chat, ai, cases, surveys, knowledge_base, appointments, analytics, etc.)
│   ├── uploads/        # receipts/, reports/
│   └── server.py
├── frontend/
│   ├── src/
│   │   ├── components/ # DashboardShell, ChatWidget, OnboardingWizard, DocumentChecklist, WorkloadDashboard, etc.
│   │   ├── pages/      # AdminDashboard, CaseManagerDashboard, ClientDashboard, BulkOperations, SLATracker, CaseTransfer, SatisfactionSurvey, KnowledgeBase, RevenueForecasting, CMPerformance, Appointments, etc.
│   │   └── App.js
└── memory/             # PRD.md, test_credentials.md
```

## Implemented Features

### Phase 1-3 — Core Portal, Advanced Features, UI/UX
- Multi-role JWT auth, role-based dashboards
- Case workflow enforcement with step locking
- Document upload/review/approval, bulk upload
- Document Expiry Tracking with Auto In-App Reminders
- Information Sheet Editor, AI Chatbot, Stripe Payments
- Shared DashboardShell with grouped collapsible sidebar

### Phase 4 — Intelligence & Monitoring
- Comprehensive Activity Log System (940+ activities tracked)
- AI Workflow Builder (10 templates, GPT-5.2 generated workflows)
- Email Service (Resend with fallback)

### Phase 5 — Communication & Productivity
- Real-Time In-App Chat (Client <-> CM)
- Client Onboarding Wizard (5-step guided)
- Smart Document Checklist (step-wise progress)
- Smart Workload Dashboard (CM productivity)

### Phase 6A — Operations (DONE - Dec 2025)
- **Bulk Operations**: Multi-case step advance + multi-document batch approve/reject
- **SLA/Deadline Tracker**: Per-step deadline setting, overdue alerts, approaching deadline warnings
- **Auto Case Assignment**: Workload-based + language preference matching (admin only)
- **Case Transfer**: CM-to-CM transfer with reason tracking, full transfer history

### Phase 6B — AI Intelligence (Pre-existing)
- AI Document Validator (passport expiry, photo specs, quality scoring)
- AI Case Risk Assessment (approval probability with factors)

### Phase 6C — Client Experience (DONE - Dec 2025)
- **Client Satisfaction Survey**: 5-star multi-category rating (overall, communication, speed, documentation), feedback text, recommendation toggle
- **Knowledge Base**: CRUD articles with categories, search, tag filtering, view counts
- **Document Annotation**: CM can add annotations to documents with page/position info

### Phase 6D — Analytics & Advanced (DONE - Dec 2025)
- **Revenue Forecasting**: Historical monthly revenue, growth rate, pipeline value, trend detection, 6-month forecast
- **CM Performance Metrics**: Per-CM stats (active/completed cases, avg completion days, satisfaction score, overdue steps)
- **Appointments**: Full scheduling system with case linking, attendee assignment, cancel/complete status

## Key API Endpoints
- Auth: `POST /api/auth/login`
- Cases: `POST /api/cases/bulk-advance`, `POST /api/cases/set-step-deadline`, `GET /api/cases/overdue-steps`, `POST /api/cases/auto-assign`, `POST /api/cases/transfer`, `GET /api/cases/transfer-history/{id}`
- Documents: `POST /api/documents/bulk-review`, `POST /api/documents/{id}/annotate`
- Analytics: `GET /api/analytics/revenue-forecast`, `GET /api/analytics/cm-performance`
- Surveys: `POST /api/surveys/submit`, `GET /api/surveys/stats`
- KB: `GET/POST/PUT/DELETE /api/knowledge-base/articles`, `GET /api/knowledge-base/categories`
- Appointments: `POST/GET /api/appointments`, `PUT /api/appointments/{id}/cancel|complete`
- Chat: `POST/GET /api/chat/conversations`, `POST/GET /api/chat/messages`
- AI: `POST /api/ai/validate-document/{id}`, `GET /api/ai/predict-approval/{id}`

## Prioritized Backlog
### Remaining from 34-point list:
- #3 Case Timeline View
- #6 Client Satisfaction Survey ✅ DONE
- #7 Multi-Language (partially — needs i18n framework)
- #8 Knowledge Base ✅ DONE
- #13 Quick Notes & Tags
- #15 Document Annotation ✅ DONE
- #16 Canned Responses for CM
- #27 Appointment Scheduling ✅ DONE
- #28 Referral Program
- #29 Client Greetings
- #30 Revenue Forecasting ✅ DONE
- #31 CM Performance Metrics ✅ DONE
- #32 Conversion Funnel
- #33 Country/Product Analytics
- #34 Commission Analytics

## Test Results
- Iteration 39: 93% backend (41/44, 3 skipped), 100% frontend — Phase 6A-6D
- Iteration 38: 100% (20/20 + frontend) — Phase 5: Chat, Onboarding, Checklist, Workload
- Iteration 37: 100% (17/17 + frontend) — Phase 4: Activity Log, AI Workflow, Email

## Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
