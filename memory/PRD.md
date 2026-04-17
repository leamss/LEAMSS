# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal (LEAMSS) with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

## Latest Session (2026-04-17)

### AI Workflow Builder - Fully Working
- **51 countries** with flags in gallery
- **AI-powered visa categories**: Click country -> AI lists ALL visa subclasses with official fees, URLs
- **AI workflow generation**: Click visa -> AI generates comprehensive workflow with 5-8 steps, 10-20 docs per workflow
- **Improved prompt**: Every step has 2-6 docs, includes Form numbers, specific fees, assessment bodies
- **Template context**: AI uses verified template data as reference for better accuracy
- **Fully editable review**: Product name, fees, steps, docs - all inline editable
- **Robust JSON parsing**: Multiple fallback strategies for AI response parsing
- **Template fallback**: When AI fails, uses verified template data
- **Save as Product**: One-click save with all steps and documents

### Document Management System
- Step-wise document management (Admin -> CM -> Client flow)
- Unified Client "Documents & Steps" view
- 8 verified templates (Canada PR, Australia PR, UK, NZ, USA H-1B, UAE Golden, Singapore EP, Student)
- CM can add/delete documents per step, AI suggest per step
- Admin workflow step editor with AI suggestions

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123
