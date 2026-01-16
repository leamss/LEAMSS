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

### Case Management
- [x] Clients upload documents according to workflow
- [x] Case Managers review documents
- [x] Workflow progress tracking
- [x] Additional document requests

### Sales & Onboarding
- [x] Partners create sales for new clients
- [x] Admin approves sales and assigns Case Managers
- [x] Client accounts created after approval

### Admin Oversight
- [x] View all cases
- [x] Manage all users (create/view/edit/delete)
- [x] User impersonation ("Switch Portal")
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

## Implementation Status (Updated: December 16, 2025)

### Completed Features ✅
1. **Admin Dashboard Overhaul**
   - Products & Workflows tab with full workflow editor
   - Add/Edit/Delete workflow steps with required documents
   - Users tab with search and user management
   - User impersonation (Switch Portal button)
   - Revenue & Commission dashboard
   - Sales approval workflow
   - Case management with reassignment

2. **Color Scheme Update**
   - All 4 dashboards updated to LEAMSS brand colors
   - Teal primary (#2a777a)
   - Orange secondary (#f7620b)
   - White card backgrounds (NO YELLOW)
   - Dark slate sidebars

3. **Flexible Commission Structure** (NEW)
   - **Fixed Percentage**: Standard commission rate per product
   - **Tiered (Volume-based)**: Commission varies by total sales count
   - **Custom (Per Partner)**: Individual rates set per partner
   - Commission type selector in product creation/edit dialog
   - Commission type badges displayed on product cards

4. **Email Notification System** (NEW)
   - Gmail SMTP integration for transactional emails
   - Professional HTML email templates with LEAMSS branding
   - Email notifications for:
     - Welcome emails with login credentials
     - Document approval/rejection
     - Step completion notifications
     - Additional document requests
     - Sale approval/rejection (for partners)
   - Graceful handling when email not configured

5. **All Portals Working**
   - Admin Portal: Full functionality
   - Partner Portal: Sales creation, commission tracking
   - Case Manager Portal: Case management, document review
   - Client Portal: Document upload, progress tracking

---

## Prioritized Backlog

### P0 (Critical) - None remaining

### P1 (High Priority)
1. **Commission Structure Enhancement**
   - Add flexible commission options per product (fixed %, tiered, custom)
   - Admin can set commission type when creating/editing products
   
2. **Document Download in Case Manager**
   - Verify document download functionality
   - Add preview capability

### P2 (Medium Priority)
3. **Ticketing System Integration**
   - Wire NotificationBell and CreateTicket components
   - User-targeted ticket creation
   
4. **Notification System**
   - Real-time notifications for case updates
   - Email notifications

### P3 (Low Priority)
5. **Backend Refactoring**
   - Split server.py into router modules
   - Improve code organization

6. **Additional Features**
   - Request additional documents (Case Manager)
   - Admin direct client creation
   - Payment gateway integration (Stripe/Razorpay)

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

## Database Collections
- users
- products
- cases
- sales
- documents
- tickets
- notifications
