# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Complete Feature List (2026-04-15 to 2026-04-17)

1. **Step-wise Document Management** - Admin/CM/Client document flow
2. **Unified Client Document View** - Single "Documents & Steps" tab
3. **Smart Template AI** - 8 verified templates, 51 countries
4. **AI Workflow Builder** - Country->Visa->Generate->Edit->Save with SVG flags
5. **Government Forms** - 48 official forms (7 countries) with download links
6. **AI Verification System** - Admin verifies AI data before saving
7. **Deadline & SLA Tracker** - Auto document expiry, manual deadlines, color-coded urgency
8. **Client Intake Form Builder** - Product-specific, role-based (Client/CM/Both), Admin-managed

### Latest: Intake Form Builder (v2 with Role-Based Fields)
- **Admin**: Intake Form Builder page - create/edit forms per product with sections, fields, role assignment
- **CM fills**: WES Reference, NOC Code, PNP Application ID, EE Profile, Visa Grant Status/Date, Funds Verified
- **Client fills**: Personal info, passport, language scores, bank details, settlement funds
- **Both can fill**: Shared fields like settlement funds
- **Visibility**: Client sees CM fields as read-only with lock icon; CM sees client fields as read-only
- **Notifications**: Client notified when CM updates fields
- **Progress tracking**: Completion % with progress bar

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
