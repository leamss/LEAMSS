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
- Step-wise Document Management System (2026-04-15): Admin workflow docs, CM step-specific + additional doc requests, backend merge logic
- **Unified Document View (2026-04-15)**: Replaced 4+ client document tabs with single "Documents & Steps" view

## Unified Document View (Latest - 2026-04-15)
### What was done:
1. **Created UnifiedDocumentView.jsx**: Single component replacing Workflow Steps, Document Checklist, Doc Completion, Action Required tabs
2. **Client sidebar cleanup**: Removed 4 redundant tabs, now: My Journey, Documents & Steps, My Uploads, My Info Sheet
3. **Progress card**: Shows completion %, stats (Required/Uploaded/Pending/Requested)
4. **Step accordion cards**: Each step expands to show required documents with Upload buttons, mandatory tags, CM notes, expiry warnings
5. **Additional docs section**: Shows CM-requested additional documents with upload
6. **Legacy data merge**: Backend reads from both `document_requests` and `additional_doc_requests` collections
7. **Admin default sync**: Auto-merges admin workflow docs into existing case_steps on API call

### Key Components:
- `/app/frontend/src/components/UnifiedDocumentView.jsx` - Unified client document view
- `/app/backend/routers/step_documents.py` - Step-wise document API with merge logic

### Key Endpoints:
- `PUT /api/products/{id}/workflow-step/{order}` - Admin save workflow step with required_documents
- `POST /api/step-documents/request-step-doc` - CM add doc to specific step
- `POST /api/step-documents/request-additional` - CM add additional doc (separate section)
- `GET /api/step-documents/case/{case_id}` - Get merged step-wise document structure
- `POST /api/step-documents/remove-step-doc` - Remove CM-added doc from step

## Backlog / Future Tasks
- P1: AI Document Suggestions per product/step (CM assistance)
- P2: Resend Email from mock to live (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration (requires API keys)

## Key DB Collections
- `cases`, `case_steps` (client step progression + required_documents)
- `workflow_steps` (admin-defined default docs per product step)
- `documents` (uploaded files)
- `document_requests` (new additional doc requests from step-documents API)
- `additional_doc_requests` (legacy additional doc requests from cases API)
- `cm_client_messages` (unified chat)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
