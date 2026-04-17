# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Core Architecture
- Frontend: React + Shadcn UI + Tailwind (dark mode)
- Backend: FastAPI + Motor (async MongoDB)
- Auth: JWT-based, bcrypt hashing
- Integrations: OpenAI GPT-5.2 (Emergent LLM Key), Stripe (Emergent Key), Resend (mock)

## Latest Session Features (2026-04-15 to 2026-04-17)

### Step-wise Document Management
- Admin adds docs to workflow steps (persists across clients)
- CM adds docs to specific steps OR additional section, can delete unwanted docs
- Client unified "Documents & Steps" tab (replaced 4 old tabs)
- Backend auto-merges admin defaults into case_steps

### Smart Template AI System (8 Templates)
- Canada PR (Express Entry): 20 docs, 6 steps, CAD $1,365, WES/IQAS
- Australia PR (189/190/491): 21 docs, 5 steps, AUD $4,640, ACS/VETASSESS
- UK Skilled Worker: 10 docs, 3 steps, GBP £719
- Student Visa (Generic): 15 docs, 3 steps
- New Zealand Skilled Migrant: 14 docs, 4 steps, NZD $3,310, NZQA
- USA H-1B: 15 docs, 3 steps, USD $460+, USCIS/DOL
- UAE Golden Visa: 12 docs, 3 steps, AED 2,800, ICP/GDRFA
- Singapore EP: 13 docs, 3 steps, SGD $105, MOM/COMPASS

### Template Gallery + AI Workflow Builder (Latest)
- Template Gallery page at /admin/ai-workflow with all 8 country templates
- Each card shows: country flag, fees, steps, docs, assessment bodies, government URLs
- "Use This Template" one-click applies template with all docs
- Review view with fee calculator, editable steps, save as product
- Custom AI Workflow builder for any country/visa type
- Search/filter templates

## Backlog / Future Tasks
- P1: Official government form templates/drafts downloadable
- P1: Deadline & SLA Tracker (auto-calculate expiry, reminders)
- P1: Client Intake Form Builder (auto-generate from product)
- P2: Fee Calculator standalone widget for clients
- P2: Resend Email live mode (requires RESEND_API_KEY)
- P3: Twilio WhatsApp full integration

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
- Test Client: test_sale_client@example.com / Client@123
