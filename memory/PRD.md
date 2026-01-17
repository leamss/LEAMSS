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
   - Document type, expiry date, validity months fields
   - Users tab with search and user management
   - User impersonation (Switch Portal button) with Return to Admin banner
   - Revenue & Commission dashboard
   - Sales approval workflow
   - Case management with reassignment
   - "Create Ticket for User" button in Users tab
   - System Settings tab with global controls

2. **Case Search/Filter Enhancement**
   - Search by Case ID, Client Name, Case Manager Name
   - Filter by Case Manager dropdown
   - Filter by Status dropdown
   - Clear filters button
   - Results count display

3. **Case Manager Workflow Customization**
   - Global toggle controlled by Admin (Settings tab)
   - When enabled, Case Managers can:
     - Request additional documents for specific workflow steps
     - Set document name, description, type
     - Set due date, expiry date, or validity months
   - "Customization Enabled" badge in CM dashboard
   - "Add Doc" button enabled only when previous step is completed
   - Documents appear in Client portal for upload

4. **Client Portal Enhanced UI (NEW)**
   - Attractive "Action Required" section with gradient design
   - Each document request in a styled card with shadows
   - Pill-style badges for: Step number, Document type, Due date, Validity
   - Separate "Uploaded Documents" section for submitted docs
   - Upload functionality fixed for additional document requests

5. **Clickable Notifications (NEW)**
   - Notifications show type-specific icons (ticket, document, sale)
   - Color-coded badges by notification type
   - "Mark all read" button
   - Click to navigate to relevant section (tickets, cases, sales)
   - Time ago display (Just now, 5m ago, 2h ago, etc.)

6. **Color Scheme Update**
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

12. **Real-time Notifications via SSE (NEW - January 17, 2026)**
    - Server-Sent Events endpoint for real-time notification delivery
    - Works through Kubernetes HTTP ingress (unlike WebSocket)
    - Connection status indicator (green = connected, yellow = polling mode)
    - Toast notifications when new events arrive
    - 60-second polling fallback for redundancy

13. **Browser Push Notifications (NEW - January 17, 2026)**
    - Desktop alerts even when portal is closed
    - Service worker handles push events
    - VAPID key authentication for secure delivery
    - "Enable Desktop Alerts" button in notification dropdown
    - Auto-cleanup of invalid subscriptions

14. **Backend Modular Architecture (NEW - January 17, 2026)**
    - Refactored monolithic server.py (2356 lines) into modular structure
    - New structure:
      - `/backend/server.py` - Main app entry point (132 lines)
      - `/backend/routers/` - 10 domain-specific routers (auth, users, products, sales, cases, documents, tickets, notifications, reports, admin)
      - `/backend/core/` - Config, auth, database, models
      - `/backend/services/` - Notification and commission services
    - Improved maintainability and code organization

15. **Ticketing System Overhaul (NEW - January 17, 2026)**
    - Users can now create tickets and assign to specific users (not just Admin)
    - Role-based recipient filtering:
      - Admin: Can send to any user
      - Case Manager: Can send to their clients + Admin (with escalation option)
      - Client: Can send to their Case Manager + Admin
      - Partner: Can send to Admin only
    - Unified `TicketSection` component integrated in all 4 portals
    - New `/api/users/ticket-recipients` endpoint for role-appropriate recipients
    - Support Tickets navigation added to CaseManager, Partner, and Client dashboards
    - Full ticket lifecycle: Open → In Progress → Resolved → Closed

16. **Admin Sales & Commission Reports Fixed (DONE - January 17, 2026)**
    - Sales report period filter: weekly, monthly, quarterly, yearly, custom date range
    - Commission report: same filters plus partner grouping
    - CSV export for both reports (via StreamingResponse)
    - PDF export via print-friendly HTML popup
    - Backend `get_date_range_from_period()` calculates proper date ranges

17. **Notification System Enhanced (DONE - January 17, 2026)**
    - Dropdown shows only unread notifications (auto-read on click)
    - "View All Notifications" button navigates to `/notifications`
    - New Notification History page with:
      - Full notification list with read/unread status
      - Search filter (by title/message)
      - Type filter (tickets, documents, sales, cases, workflow)
      - Status filter (all, unread, read)
      - Delete individual notifications
      - Mark all as read button
    - Backend DELETE endpoint added for notifications

18. **Case Manager Portal Enhanced (DONE - January 17, 2026)**
    - New "Pending Review" section:
      - Shows real-time count in sidebar with animated badge
      - Lists documents awaiting review across all assigned cases
      - Quick review/view buttons for each document
    - New "All Documents" section:
      - Searchable document table with filters
      - Filter by: document type, status (uploaded/approved/rejected)
      - Shows client name, case ID, upload date
      - Quick review action for pending documents

19. **Modern UI/UX Redesign (DONE - January 17, 2026)**
    - All 3 dashboards (Admin, Case Manager, Partner) redesigned to match Client Portal
    - Modern white sidebar with:
      - LEAMSS logo and portal name
      - Teal (#2a777a) accent on active navigation
      - User profile at bottom (avatar, name, email)
      - Logout button with hover effect
    - Sticky header with backdrop blur effect
    - Modern card design with subtle shadows and hover transitions
    - Typography: Manrope for headings, Public Sans for body
    - Consistent color palette: teal primary, orange accent

20. **Final User Feedback Refinements (DONE - January 17, 2026)**
    - **Enhanced Ticket Detail View**: All user portals (Client, Case Manager, Partner) now have the same detailed ticket view as Admin:
      - Full-page detail view with "Back to Tickets" button
      - Ticket info card with status/priority badges
      - Resolution note input (required for resolve/close - min 10 chars)
      - Attachments section with upload capability (max 10MB)
      - Messages section with reply input and send button
      - Activity log showing ticket history
      - Status action buttons (Start, Resolve, Close)
    - **Notification Click Navigation**: Clicking a notification navigates directly to the relevant item without page reload:
      - Ticket notifications → Support tab and opens ticket detail view
      - Document notifications → Action Required tab for Client
      - Custom `onNotificationClick` handlers in all dashboards
    - **Delete Permissions**: All delete operations restricted to Admin only:
      - Backend delete endpoints protected with `require_role([UserRole.ADMIN])`
      - Non-admin users receive 403 Forbidden when attempting delete
    - **Client Portal "Action Required" Focus**: When navigated from a document notification, automatically switches to Action Required tab

---

## Prioritized Backlog

### P0 (Critical) - None remaining

### P1 (High Priority)
1. **Configure Gmail Credentials** (User Action Required)
   - User needs to set GMAIL_EMAIL and GMAIL_APP_PASSWORD in backend/.env
   - Instructions provided in .env file
   - Once configured, expiry emails will be sent automatically

### P2 (Medium Priority)
2. **Ticket System Analytics**
   - Ticket categories analytics
   - SLA tracking
   - Auto-assignment rules

### P3 (Low Priority)
3. **Payment Gateway Integration**
   - Stripe/Razorpay integration for payments
   - Commission payout tracking

---

## Recently Completed

### Document Expiry Reminders (DONE - January 17, 2026)
- **Automated daily background checker** runs on server startup and every 24 hours
- Sends notifications at 30, 14, 7, 3, and 1 days before expiry
- **Dual notification system:**
  - In-app notifications to both client and case manager
  - Email notifications (when Gmail is configured)
- **Admin Dashboard section** showing "Documents Expiring Soon"
- Color-coded urgency badges (red ≤3 days, amber ≤7 days, yellow ≤30 days)
- "Send Reminders Now" button for manual trigger
- Prevents duplicate reminders via `expiry_reminders` collection
- **API Endpoints:**
  - `GET /api/scheduler/expiring-documents` - List expiring docs
  - `POST /api/scheduler/run-expiry-check-now` - Trigger immediate check

---

## API Endpoints
- `/api/auth/login` - Authentication
- `/api/admin/users` - User management
- `/api/products` - Product CRUD
- `/api/products/workflow-step` - Add workflow step
- `/api/products/{id}/workflow-step/{order}` - Update/Delete workflow step
- `/api/cases` - Case management (now returns case_manager_name for filtering)
- `/api/cases/{case_id}/custom-document-request` - CM custom doc request
- `/api/cases/request-additional-document` - Request additional document
- `/api/sales/pending` - Pending sales approval
- `/api/sales/approve` - Approve/reject sales
- `/api/stats/dashboard` - Dashboard statistics
- `/api/admin/impersonate/{user_id}` - User impersonation
- `/api/settings` - GET/PUT system settings
- `/api/tickets` - Create ticket
- `/api/tickets/all` - Get all tickets (with filters)
- `/api/tickets/stats` - Get ticket statistics
- `/api/tickets/my-tickets` - Get user's tickets
- `/api/tickets/{id}` - Get ticket details
- `/api/tickets/{id}/status` - Update ticket status (body: {status, resolution_note})
- `/api/tickets/{id}/message` - Add message to ticket
- `/api/tickets/{id}/attachment` - Upload attachment (POST)
- `/api/tickets/{id}/attachment/{file_id}` - Download attachment (GET)
- `/api/users/ticket-recipients` - **NEW**: Get role-appropriate ticket recipients
- `/api/reports/sales` - Sales report with filters
- `/api/reports/partner-commissions` - Partner commission data
- `/api/notifications/stream` - SSE endpoint for real-time notifications (query param: token)
- `/api/push/vapid-public-key` - Get VAPID public key for push subscription
- `/api/push/subscribe` - Subscribe to push notifications
- `/api/push/unsubscribe` - Unsubscribe from push notifications
- `/api/push/subscriptions` - List user's push subscriptions

## Database Collections
- users
- products
- cases
- sales
- documents
- tickets
- notifications
- push_subscriptions
