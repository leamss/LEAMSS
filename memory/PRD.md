# LEAMSS Immigration Portal — Product Requirements Document

## Original Problem Statement
Comprehensive immigration service portal with Admin, Case Manager, Partner, and Client roles. Multi-step case workflows, document management, ticketing, analytics, and payment processing. 34 advanced features across Phases 1-7.

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
- Document Upload & Review
- Ticketing System
- Notifications (with SSE real-time stream)
- User Management

### Phase 4: Intelligence (ALL VERIFIED)
- Activity Log (Live Feed, By User, By Type)
- Global Search
- AI Workflow Builder (GPT-5.2)
- AI Chat Widget
- Analytics Dashboard

### Phase 5: Communication (ALL VERIFIED)
- Chat System (conversations + messages)
- Email Service (Resend — mock mode)
- Client Onboarding Wizard

### Phase 6: Operations & Analytics (ALL VERIFIED)
- Bulk Case Advance & Bulk Document Review
- SLA Tracker
- Case Transfer & Auto Assignment
- Satisfaction Surveys (NPS)
- Knowledge Base
- Appointments
- Revenue Forecasting & CM Performance Analytics

### Phase 7: Productivity & Growth (ALL VERIFIED)
- Case Timeline View
- Quick Notes & Tags
- Canned Responses
- Referral Program
- Client Greetings
- Conversion Funnel, Country/Product, Commission Analytics

### Client Self-Service Portal (NEW — ALL VERIFIED)
- **My Case Journey** — Flight-tracker style visual case progress with airplane icon, stats (% complete, steps done, docs, days active), current step highlight, expandable step-by-step timeline
- **Message Center** — Dedicated WhatsApp-style chat interface with conversation list, search, new conversation, send messages
- **My Profile** — Profile editing (name, mobile, language), change password, notification preferences toggles (6 options)
- Clean layout: Dedicated pages hide overview widgets for full-screen experience

### Cross-cutting (ALL VERIFIED)
- Multi-Language Toggle (Hindi/English — shell level)
- Stripe Payment Integration
- Document Expiry Tracker
- Client Happiness Score (NPS widget)
- SSE Real-time Notification Stream

## Current Bugs: NONE

## Backlog (Prioritized)
- **P1**: Extend i18n translations to inner page content (stats cards, tables, forms)
- **P2**: Wire Resend Email to live dispatch (requires user's RESEND_API_KEY)
- **P2**: PDF Report Generation
- **P2**: Bulk Document Upload (multi-file at once)
- **P3**: SMS Notifications (Twilio)
- **P3**: Google Calendar Integration for deadlines
- **P3**: Migrate LanguageProvider to react-i18next for scale

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Test Reports
- iteration_41.json: 52/52 backend tests PASSED (all 34 features)
- iteration_42.json: 19/19 backend + frontend ALL PASS (Client Self-Service Portal)
