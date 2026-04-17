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
- AI Document Suggestions v1 (2026-04-15): Basic GPT-powered suggestions
- **Smart Template + Web Search AI (2026-04-15)**: Accurate government-verified document templates

## Smart Template AI System (Latest - 2026-04-15)
### What was built:
1. **Immigration Templates**: Real document requirements for Canada PR, Australia PR (189/190/491), UK Skilled Worker, Student Visa
2. **Template-first approach**: If product matches template, return verified docs instantly (no AI needed)
3. **Real data included**: Assessment bodies (WES/ACS/VETASSESS), government fees (CAD $1,365, AUD $4,640, GBP £719), official URLs
4. **AI fallback**: Web search + GPT for products without templates
5. **Templates API**: GET /api/step-documents/templates lists all available templates
6. **Audit trail**: Different log actions for template vs AI suggestions

### Templates Available:
- Canada PR (Express Entry): 20 docs, 6 steps, CAD $1,365
- Australia PR (189/190/491): 21 docs, 5 steps, AUD $4,640
- UK Skilled Worker: 10 docs, 3 steps, GBP £719
- Student Visa (Generic): 15 docs, 3 steps

## Backlog / Future Tasks
- Tool enhancements (user to confirm priorities)
- P2: Resend Email from mock to live (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration (requires API keys)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
