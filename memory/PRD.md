# LEAMSS Portal - Product Requirements Document

## Original Problem Statement
Build a comprehensive "LEAMSS Portal" for an immigration service with four distinct user roles: Admin, Case Manager, Partner, and Client. The portal needs dynamic workflow management for immigration products.

## User Personas
1. **Admin**: Full system control, user management, sales approval, revenue tracking
2. **Case Manager**: Process cases, review documents, communicate with clients
3. **Partner**: Create sales, onboard clients, track commissions
4. **Client**: Upload documents, track case progress

## Core Requirements

### Role-Based Access Control
- [x] Separate dashboards for Admin, Case Manager, Partner, Client
- [x] JWT-based authentication
- [x] Role-specific routes and permissions

### Dynamic Workflow Management (Admin)
- [x] Create and edit products
- [x] Define multi-stage workflows for each product
- [x] Each stage has: name, description, duration, required documents
- [x] Add/Edit/Delete workflow steps
- [x] Document requirements per step with mandatory flag
- [x] **NEW**: Document type, expiry date, validity months per document

### Case Management
- [x] Clients upload documents according to workflow
- [x] Case Managers review documents
- [x] Workflow progress tracking
- [x] Additional document requests
- [x] **NEW**: Case Manager workflow customization (when enabled by Admin)

### Case Search/Filter (Admin)
- [x] **NEW**: Search by Case ID, Client Name, Case Manager Name
- [x] **NEW**: Filter by Case Manager (dropdown)
- [x] **NEW**: Filter by Status (Active, Completed, On Hold)

### System Settings (Admin)
- [x] **NEW**: Global settings management
- [x] **NEW**: Toggle for Case Manager workflow customization authority

### Sales & Onboarding
- [x] Partners create sales for new clients
- [x] Admin approves sales and assigns Case Managers
- [x] Client accounts created after approval

### Admin Oversight
- [x] View all cases with advanced filtering
- [x] Manage all users (create/view/edit/delete)
- [x] User impersonation ("Switch Portal") with Return to Admin banner
- [x] Sales/Revenue dashboard with commission tracking
- [x] Search functionality for users

### UI/UX
- [x] Brand colors: #f7620b (orange), #2a777a (teal), #d81f26 (red)
- [x] Professional styling inspired by leamss.com
- [x] White card backgrounds (no yellow)
- [x] Consistent color scheme across all portals

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Backend**: FastAPI, Python
- **Database**: MongoDB
- **Authentication**: JWT tokens

## Color Scheme
- Primary (Teal): #2a777a - Navigation, primary buttons, progress
- Secondary (Orange): #f7620b - Create actions, warnings, accents
- Destructive (Red): #d81f26 - Delete buttons, errors
- Background: #F5F7FA (light gray)
- Cards: White
- Sidebar: slate-800

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- Case Manager: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## File Structure
```
/app
├── backend/
│   ├── server.py       # Main FastAPI app
│   ├── seed_data.py    # Demo data script
│   └── .env
└── frontend/
    ├── src/
    │   ├── App.js
    │   ├── index.css   # Global styles with LEAMSS colors
    │   ├── components/
    │   └── pages/
    │       ├── AdminDashboard.jsx
    │       ├── CaseManagerDashboard.jsx
    │       ├── ClientDashboard.jsx
    │       ├── PartnerDashboard.jsx
    │       └── Login.jsx
    └── package.json
```

---

## Implementation Status (Updated: January 17, 2026)

### Completed Features ✅
1. **Admin Dashboard Overhaul**
   - Products & Workflows tab with full workflow editor
   - Add/Edit/Delete workflow steps with required documents
   - **NEW**: Document type, expiry date, validity months fields
   - Users tab with search and user management
   - User impersonation (Switch Portal button) with Return to Admin banner
   - Revenue & Commission dashboard
   - Sales approval workflow
   - Case management with reassignment
   - "Create Ticket for User" button in Users tab
   - **NEW**: System Settings tab with global controls

2. **Case Search/Filter Enhancement (NEW)**
   - Search by Case ID, Client Name, Case Manager Name
   - Filter by Case Manager dropdown
   - Filter by Status dropdown
   - Clear filters button
   - Results count display

3. **Case Manager Workflow Customization (NEW)**
   - Global toggle controlled by Admin (Settings tab)
   - When enabled, Case Managers can:
     - Request additional documents for specific workflow steps
     - Set document name, description, type
     - Set due date, expiry date, or validity months
   - "Customization Enabled" badge in CM dashboard
   - "Add Doc" button on each workflow step

4. **Color Scheme Update**
   - All 4 dashboards updated to LEAMSS brand colors
   - Teal primary (#2a777a)
   - Orange secondary (#f7620b)
   - White card backgrounds (NO YELLOW)
   - Dark slate sidebars

5. **Flexible Commission Structure** 
   - **Fixed Percentage**: Standard commission rate per product
   - **Tiered (Volume-based)**: Commission varies by total sales count (FIXED)
   - **Custom (Per Partner)**: Individual rates set per partner
   - Commission type selector in product creation/edit dialog
   - Commission type badges displayed on product cards

6. **Email Notification System**
   - Gmail SMTP integration for transactional emails
   - Professional HTML email templates with LEAMSS branding
   - Email notifications for key events
   - Graceful handling when email not configured

7. **Total Sales Report Section**
   - Search by partner
   - Filter by period (Lifetime, Weekly, Monthly, Yearly, Custom date range)
   - Summary cards (Total Sales, Approved, Revenue, Commission)
   - Sales records table with export to CSV

8. **Partner Commissions Section**
   - View commission payable to each partner
   - Breakdown by Weekly, Monthly, Yearly, Lifetime
   - Total revenue generated per partner
   - Export all commission data

9. **Support Tickets Section**
   - Full ticket management system
   - Filter by Status, Priority, Role
   - Resolution note validation (required for resolve/close)
   - File attachments upload/download (max 10MB)
   - Activity log tracking all changes
   - User targeting - assign to specific users or roles
   - Create ticket directly for a user from Users tab
   - Ticket messaging/replies

10. **Admin Impersonation UX Improvement**
    - Admin token preserved when switching to another user
    - "Return to Admin" banner displayed on impersonated user's dashboard
    - One-click return to admin account without re-login

11. **All Portals Working**
    - Admin Portal: Full functionality
    - Partner Portal: Sales creation, commission tracking
    - Case Manager Portal: Case management, document review, workflow customization
    - Client Portal: Document upload, progress tracking

---

## Prioritized Backlog

### P0 (Critical) - None remaining

### P1 (High Priority)
1. **Configure Gmail Credentials** (User Action Required)
   - User needs to set GMAIL_EMAIL and GMAIL_APP_PASSWORD in backend/.env
   - Instructions provided in .env file

2. **Commission "Effective Date" for Commission Changes**
   - Add date picker when editing product commission
   - Implement historical commission lookup based on sale date
   - Commission history array in product model

### P2 (Medium Priority)
3. **Real-time Notifications**
   - WebSocket for instant notification updates
   - Push notifications

4. **Ticket System Analytics**
   - Ticket categories analytics
   - SLA tracking
   - Auto-assignment rules

### P3 (Low Priority)
5. **Backend Refactoring**
   - Split server.py into router modules (admin.py, tickets.py, reports.py, etc.)
   - Improve code organization

6. **Payment Gateway Integration**
   - Stripe/Razorpay integration for payments
   - Commission payout tracking

---

## API Endpoints
- `/api/auth/login` - Authentication
- `/api/admin/users` - User management
- `/api/products` - Product CRUD
- `/api/products/workflow-step` - Add workflow step
- `/api/products/{id}/workflow-step/{order}` - Update/Delete workflow step
- `/api/cases` - Case management
- `/api/sales/pending` - Pending sales approval
- `/api/sales/approve` - Approve/reject sales
- `/api/stats/dashboard` - Dashboard statistics
- `/api/admin/impersonate/{user_id}` - User impersonation
- `/api/tickets` - Create ticket
- `/api/tickets/all` - Get all tickets (with filters)
- `/api/tickets/stats` - Get ticket statistics
- `/api/tickets/{id}` - Get ticket details
- `/api/tickets/{id}/status` - Update ticket status (body: {status, resolution_note})
- `/api/tickets/{id}/message` - Add message to ticket
- `/api/tickets/{id}/attachment` - Upload attachment (POST)
- `/api/tickets/{id}/attachment/{file_id}` - Download attachment (GET)
- `/api/reports/sales` - Sales report with filters
- `/api/reports/partner-commissions` - Partner commission data

## Database Collections
- users
- products
- cases
- sales
- documents
- tickets
- notifications
