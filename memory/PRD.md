# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Latest Fix (2026-04-17)
- **BUGFIX**: "Failed to load visa categories" - visa-categories endpoint now uses hardcoded data from COUNTRY_REFERENCES (no AI needed)
- **BUGFIX**: Generate workflow has template fallback when AI fails (uses step_documents templates)
- **BUGFIX**: Removed duplicate visa categories in frontend

## Current State
- 51 countries worldwide with visa categories
- 8 verified templates with real government data
- Fully editable review view (name, fees, steps, docs - all inline editable)
- Template-first approach works without AI
- AI enrichment is optional (when budget available)

## Known Limitation
- LLM Budget exceeded - AI enrichment won't work until topped up
- All core flows work via templates/hardcoded data

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
