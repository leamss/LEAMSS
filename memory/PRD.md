# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Latest Changes (2026-04-17)

### AI Verification System (Option B)
- AI-generated workflows show amber "Verification Required" banner
- "Verify on Official Website" button links to government source
- Admin must check "I have verified" checkbox before saving
- Save button disabled until verification checkbox checked
- Template workflows show blue "Verified Template" notice
- Green "Verified by Admin" banner after verification

### Government Forms (Admin/CM only)
- 48 forms across 7 countries (Australia, Canada, USA, UK, NZ, UAE, Singapore)
- Visible in Admin AI Workflow Builder review view
- Removed from Client portal (CM shares links directly)

### Complete Feature Set
- 51 countries, AI visa categories, comprehensive workflow generation
- 8 verified templates with real government data
- Fully editable review (name, fees, steps, docs)
- Step-wise document management, unified client view
- CM doc management with AI suggestions

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
