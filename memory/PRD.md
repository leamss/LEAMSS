# LEAMSS Immigration Portal — PRD

## Tech Stack
React + TailwindCSS + Shadcn UI | FastAPI + Motor (MongoDB) | OpenAI GPT-5.2 | Stripe | Resend (mock) | PWA

## ALL Features Complete & Verified

### Core: Phases 1-13, P2, All Overhauls
### Step-wise Document Management (Latest — ALL VERIFIED):
- Admin: Define default documents per workflow step (source: admin_default)
- CM: Request step-level docs (only for that client) + Additional docs (separate section)
- Client: Step-wise view with per-doc upload, progress bars, mandatory/optional tags
- Delete control: CM removes only CM-added; Admin removes any
- Document types: admin_default, cm_request | Tags: mandatory, optional, conditional

## Current Bugs: NONE

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Remaining
- Resend Email live (needs RESEND_API_KEY)
- WhatsApp Twilio (needs API key)
