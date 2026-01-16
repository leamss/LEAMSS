# LEAMSS Immigration Portal

## Overview
A comprehensive immigration and visa consulting management system with 4 role-based portals for streamlined case management, sales tracking, and client communication.

## Features

### 🎯 Core Functionality
- **4 Role-Based Portals**: Admin, Case Manager, Partner/Sales, Client
- **Sales Management**: Complete sales workflow from creation to approval
- **Case Management**: Multi-step workflow system with customizable stages
- **Document Management**: Secure upload, review, and approval system using MongoDB GridFS
- **Commission Tracking**: Automated commission calculation for partners
- **User Management**: Role-based access control with secure authentication

### 👥 User Roles

#### Admin (Owner)
- Approve/reject sales submissions
- Create cases and assign case managers
- Configure products/services and workflow templates
- Manage users (case managers, partners)
- View all cases, documents, and reports
- Access dashboard with key metrics

#### Case Manager
- View and manage assigned cases only
- Follow product-specific workflow steps
- Review, approve, or reject client documents
- Update case step statuses
- Add internal notes and track progress

#### Partner/Sales
- Create new sales with client details
- Upload mandatory documents (payment receipt, agreement, passport)
- View sales status and history
- Track commission earnings
- Access sales performance dashboard

#### Client
- View case information and progress
- Follow step-wise checklist
- Upload required documents per workflow step
- View document review status and comments
- Track case manager communications

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT tokens with bcrypt password hashing
- **File Storage**: MongoDB GridFS
- **API Style**: RESTful with automatic OpenAPI documentation

### Frontend
- **Framework**: React 19
- **Styling**: Tailwind CSS with custom design system
- **UI Components**: Shadcn/UI (Radix UI primitives)
- **Routing**: React Router v7
- **HTTP Client**: Axios
- **Form Handling**: React Hook Form
- **Notifications**: Sonner

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB running on localhost:27017

### Backend Setup
```bash
cd /app/backend

# Install dependencies
pip install -r requirements.txt

# Seed database with demo data
python seed_data.py

# Server runs on port 8001 (managed by supervisor)
```

### Frontend Setup
```bash
cd /app/frontend

# Install dependencies
yarn install

# Development server runs on port 3000 (managed by supervisor)
```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@leamss.com | Admin@123 |
| Case Manager | manager@leamss.com | Manager@123 |
| Partner | partner@leamss.com | Partner@123 |
| Client | client@leamss.com | Client@123 |

## API Documentation

### Authentication
```bash
# Login
POST /api/auth/login
Body: {"email": "admin@leamss.com", "password": "Admin@123"}
Response: {"token": "jwt_token", "user": {...}}

# Register (Admin only)
POST /api/auth/register
Headers: {"Authorization": "Bearer <token>"}
Body: {"email": "...", "name": "...", "role": "...", "password": "..."}
```

### Products
```bash
# Create product (Admin)
POST /api/products

# Get all products
GET /api/products

# Add workflow step to product (Admin)
POST /api/products/workflow-step
```

### Sales
```bash
# Create sale (Partner)
POST /api/sales

# Get my sales (Partner)
GET /api/sales/my-sales

# Get pending sales (Admin)
GET /api/sales/pending

# Approve/reject sale (Admin)
POST /api/sales/approve
```

### Cases
```bash
# Get my cases (Case Manager/Client/Partner)
GET /api/cases/my-cases

# Get all cases (Admin)
GET /api/cases

# Get case details
GET /api/cases/{case_id}

# Update workflow step (Case Manager/Admin)
POST /api/cases/update-step
```

### Documents
```bash
# Upload document
POST /api/documents/upload
Content-Type: multipart/form-data

# Get case documents
GET /api/documents/case/{case_id}

# Review document (Case Manager/Admin)
POST /api/documents/review
```

## Project Structure

```
/app/
├── backend/
│   ├── server.py              # Main FastAPI application
│   ├── seed_data.py           # Database seeding script
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── PartnerDashboard.jsx
│   │   │   ├── CaseManagerDashboard.jsx
│   │   │   └── ClientDashboard.jsx
│   │   ├── components/ui/     # Shadcn UI components
│   │   ├── App.js             # Main React component
│   │   └── index.css          # Global styles
│   ├── package.json
│   └── .env
└── design_guidelines.json     # UI/UX design system
```

## Workflows

### Sale to Case Creation Flow
1. Partner creates a new sale with client details and uploads mandatory documents
2. Admin reviews and approves/rejects the sale
3. On approval:
   - System auto-creates a Client user account
   - System auto-creates a Case with workflow steps
   - Case Manager is assigned
   - Client receives invitation (email notification - to be implemented)

### Document Review Flow
1. Client uploads documents for specific workflow steps
2. Case Manager receives notification of new uploads
3. Case Manager reviews and approves/rejects/requests revision
4. Client sees updated document status and comments

### Workflow Step Management
1. Admin creates products with custom workflow steps
2. Each step has: name, order, description
3. When case is created, workflow steps are copied from product
4. Case Manager updates step statuses: pending → in_progress → completed

## Design System

### Color Palette
- **Primary**: Deep Slate (#0F172A) - Navigation, headings
- **Secondary**: Off-White (#F8FAFC) - Page backgrounds
- **Accent**: Electric Blue (#2563EB) - CTAs, links
- **Success**: Visa Green (#059669) - Approvals
- **Warning**: Pending Amber (#D97706) - Pending actions
- **Error**: Reject Red (#DC2626) - Rejections

### Typography
- **Headings**: Merriweather (serif) - Professional, trustworthy
- **Body**: Inter (sans-serif) - Clean, readable

### Components
- All interactive elements have hover states
- Status badges with color-coded indicators
- Responsive grid layouts
- Dark sidebar with light content area

## Security Features

- JWT-based authentication with token expiry
- Bcrypt password hashing
- Role-based access control (RBAC)
- API endpoint protection with role verification
- Secure file upload with type validation
- MongoDB GridFS for secure document storage

## Database Schema

### Collections

**users**
- id, email, name, role, mobile, password (hashed), created_at

**products**
- id, name, description, fee, commission_rate, workflow_steps[], created_at

**sales**
- id, partner_id, client info, product_id, fee_amount, amount_received, payment details, status, commission info, documents[], created_at

**cases**
- id, case_id (unique), client_id, product_id, case_manager_id, partner_id, status, current_step, steps[], created_at

**documents**
- id (GridFS file_id), filename, case_id, uploaded_by, upload_date, status, step_name, review_comment

## Future Enhancements

### Phase 2
- Email notifications (sale approval, case assignment, document status)
- Ticketing/support system for case-related queries
- Advanced reporting and analytics
- Payment gateway integration
- Multi-country workflow support
- WhatsApp integration for notifications
- Mobile app (React Native)
- Document templates and auto-generation
- Calendar integration for appointments
- Advanced search and filtering

## Testing

The application has been tested for:
- ✅ Login functionality for all 4 roles
- ✅ Role-based access control
- ✅ Sales creation and approval workflow
- ✅ Case creation and assignment
- ✅ Document upload and review
- ✅ Workflow step management
- ✅ Commission calculation
- ✅ Dashboard statistics

## Support

For issues or questions:
1. Check the demo credentials are correctly entered
2. Ensure MongoDB is running on localhost:27017
3. Verify backend and frontend services are running (supervisor status)
4. Check browser console for frontend errors
5. Check backend logs: `tail -f /var/log/supervisor/backend.err.log`

## License

Proprietary - LEAMSS Immigration Services

---

**Built with Emergent** 🚀
