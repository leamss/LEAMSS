# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Latest Feature: Deadline & SLA Tracker (2026-04-17)
- Auto-detects document expiry from uploads (passport 10yr, IELTS 2yr, medical 1yr, PCC 1yr, etc.)
- Manual deadlines: visa deadlines, processing SLAs, milestones, custom
- Color-coded urgency: Red (expired/critical), Amber (urgent), Yellow (warning), Green (safe)
- Filter pills: All/Expired/Critical/Urgent/Warning/Safe
- Client portal: "Deadlines" tab - view all deadlines
- CM Dashboard: "Deadlines & SLA" tab - view + create + delete deadlines
- Admin Dashboard: DeadlineOverviewWidget on overview - shows top urgent alerts across all cases
- Auto-notifications to client when CM creates deadline

## Session Summary (2026-04-15 to 2026-04-17)
- Step-wise Document Management System
- Unified Client Document View
- Smart Template AI (8 templates, 51 countries)
- AI Workflow Builder (country->visa->generate->edit->save)
- Government Forms (48 forms, 7 countries)
- AI Verification System (Option B)
- SVG Flags + UI Redesign
- Deadline & SLA Tracker

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
