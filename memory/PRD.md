# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Core Architecture
- Frontend: React + Shadcn UI + Tailwind (dark mode)
- Backend: FastAPI + Motor (async MongoDB)
- Auth: JWT-based, bcrypt hashing
- Integrations: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Emergent Key), Resend (mock)

## Latest Features (2026-04-17)

### AI Workflow Builder - 51 Countries + Fully Editable
- **51 countries worldwide** with flags: Argentina to Vietnam
- **Country -> Visa Subclass flow**: Click country -> AI lists all visa categories with subclass numbers, fees, official URLs
- **Fully editable review**: Product name, description, fees, step names, duration, documents - all editable inline
- **Document CRUD**: Add/edit/delete documents per step with mandatory/optional toggle
- **Step CRUD**: Add/reorder/delete workflow steps
- **8 Verified Templates**: Instant apply without AI (Canada PR, Australia PR, UK, NZ, USA H-1B, UAE Golden, Singapore EP, Student)
- **Save as Product**: One-click save with all steps and docs

### Previous Features (Same Session)
- Step-wise Document Management System
- Unified Client Document View
- Smart Template AI System (8 templates with real government data)
- CM doc delete, Admin save fix

## Backlog
- P1: Official government form templates downloadable
- P1: Deadline & SLA Tracker
- P1: Client Intake Form Builder
- P2: Fee Calculator widget for clients
- P2: Resend Email live mode
- P3: WhatsApp full integration

## Known Limitation
- LLM Budget exceeded - AI-based generation/visa-categories will fail until budget is topped up
- Template-based flows work without AI

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
