# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Core Architecture
- Frontend: React + Shadcn UI + Tailwind (dark mode support)
- Backend: FastAPI + Motor (async MongoDB)
- Auth: JWT-based, bcrypt password hashing
- Integrations: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Emergent Key), Resend (mock mode)

## Completed Phases
- Phase 1-9: Core CRUD, auth, cases, documents, payments, partner portal, notifications
- Phase 10: Admin Unified Approval Center, Refund Manager, Revenue Dashboard
- Phase 11-12: CM Smart Workload, Client EMI tracking, Eligibility Check
- Phase 13: Dark Mode, PWA, WhatsApp floating button, i18n
- Chat Unification: Unified cm_client_messages collection
- Payment Reminders UI enhancements
- Step-wise Document Management System (2026-04-15): Backend merge logic, CM routing fix
- Unified Document View (2026-04-15): Single "Documents & Steps" client tab replacing 4 tabs
- **AI Document Suggestions (2026-04-15)**: GPT-powered document checklist generation

## AI Document Suggestions (Latest - 2026-04-15)
### What was built:
1. **Backend AI endpoints**:
   - `POST /api/step-documents/ai-suggest-step-docs` - AI suggests 3-6 docs for a specific step
   - `POST /api/step-documents/ai-suggest-bulk` - AI suggests docs for ALL steps at once
2. **Admin UI**: 
   - "AI Auto-Fill Docs" button in workflow editor (bulk suggests for all steps)
   - "AI Suggest" button per step in step editor
3. **CM UI**: "AI Suggest" button per step in case detail (auto-adds suggested docs to client's step)
4. **Audit Trail**: All AI suggestions logged to audit_logs collection

### Key Endpoints:
- `POST /api/step-documents/ai-suggest-step-docs` - Per-step AI suggestions
- `POST /api/step-documents/ai-suggest-bulk` - Bulk AI suggestions for product

## Backlog / Future Tasks
- P2: Resend Email from mock to live (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration (requires API keys)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
