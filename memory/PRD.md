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
- **Step-wise Document Management System (2026-04-15)**: Admin workflow docs, CM step-specific + additional doc requests, Client step-organized view with admin doc sync

## Step-wise Document System (Latest - 2026-04-15)
### What was fixed:
1. **Backend merge logic**: `GET /api/step-documents/case/{id}` now merges admin-default docs from `workflow_steps_col` into `case_steps_col` and syncs them to DB
2. **CM routing fix**: "+Add Doc" in step now uses `POST /api/step-documents/request-step-doc` (was using wrong endpoint `custom-document-request`)
3. **Additional doc routing**: "Request Additional Document" now uses `POST /api/step-documents/request-additional`
4. **Field normalization**: Handles both `doc_name` and `name` fields throughout

### Key Endpoints:
- `PUT /api/products/{id}/workflow-step/{order}` - Admin save workflow step with required_documents
- `POST /api/step-documents/request-step-doc` - CM add doc to specific step
- `POST /api/step-documents/request-additional` - CM add additional doc (separate section)
- `GET /api/step-documents/case/{case_id}` - Get merged step-wise document structure
- `POST /api/step-documents/remove-step-doc` - Remove CM-added doc from step

## Backlog / Future Tasks
- P2: Resend Email from mock to live (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration (requires API keys)

## Key DB Collections
- `cases`, `case_steps` (client step progression + required_documents)
- `workflow_steps` (admin-defined default docs per product step)
- `documents` (uploaded files)
- `document_requests` (additional doc requests)
- `cm_client_messages` (unified chat)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
