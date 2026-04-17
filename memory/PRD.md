# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Core Architecture
- Frontend: React + Shadcn UI + Tailwind (dark mode support)
- Backend: FastAPI + Motor (async MongoDB)
- Auth: JWT-based, bcrypt password hashing
- Integrations: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Emergent Key), Resend (mock mode)

## Completed Features (Latest Session - 2026-04-15/17)

### Step-wise Document Management System
- Admin adds required docs to workflow steps (persists across all clients)
- CM adds docs to specific steps OR separate additional section
- Client sees unified "Documents & Steps" tab (replaced 4 old tabs)
- Backend merges admin defaults into case_steps automatically

### Smart Template AI Document Suggestions
- **8 Country Templates** with REAL government-verified data:
  - Canada PR (Express Entry): 20 docs, 6 steps, CAD $1,365
  - Australia PR (189/190/491): 21 docs, 5 steps, AUD $4,640
  - UK Skilled Worker: 10 docs, 3 steps, GBP £719
  - Student Visa (Generic): 15 docs, 3 steps
  - New Zealand Skilled Migrant: 14 docs, 4 steps, NZD $3,310
  - USA H-1B: 15 docs, 3 steps, USD $460+
  - UAE Golden Visa: 12 docs, 3 steps, AED 2,800
  - Singapore EP: 13 docs, 3 steps, SGD $105
- Template-first approach (instant, no AI call for known products)
- AI + Web Search fallback for unknown products
- Admin "AI Auto-Fill Docs" and per-step "AI Suggest" buttons
- CM "AI Suggest" per step + delete button for unwanted docs

### Bug Fixes (2026-04-17)
- Admin save workflow step after AI suggest (NaN duration_days, regex escaping)
- CM can delete AI-suggested/CM-added docs via X button

## Backlog / Future Tasks
- User requested: AI Workflow Builder worldwide integration
- User requested: Official government form templates/drafts downloadable
- Tool enhancements: Fee Calculator, Deadline Tracker, Client Intake
- P2: Resend Email live mode (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
