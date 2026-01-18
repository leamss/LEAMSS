-- ============================================================
-- LEAMSS Portal - MySQL Database Schema
-- Immigration Service Management System
-- ============================================================

-- Drop database if exists and create fresh
DROP DATABASE IF EXISTS leamss_portal;
CREATE DATABASE leamss_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE leamss_portal;

-- ============================================================
-- 1. USERS TABLE
-- ============================================================
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role ENUM('admin', 'case_manager', 'partner', 'client') NOT NULL,
    mobile VARCHAR(20),
    status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
    commission_rate DECIMAL(5,2) DEFAULT 0.00,
    profile_image VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- ============================================================
-- 2. PRODUCTS TABLE (Immigration Services/Visa Types)
-- ============================================================
CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    fee DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    commission_rate DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    commission_type ENUM('fixed', 'percentage', 'tiered') DEFAULT 'fixed',
    commission_effective_from DATE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_name (name)
) ENGINE=InnoDB;

-- ============================================================
-- 3. COMMISSION TIERS TABLE (For tiered commission)
-- ============================================================
CREATE TABLE commission_tiers (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    product_id VARCHAR(36) NOT NULL,
    min_sales INT NOT NULL DEFAULT 0,
    max_sales INT,
    commission_rate DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product (product_id)
) ENGINE=InnoDB;

-- ============================================================
-- 4. COMMISSION HISTORY TABLE
-- ============================================================
CREATE TABLE commission_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    product_id VARCHAR(36) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL,
    commission_type ENUM('fixed', 'percentage', 'tiered') NOT NULL,
    effective_from DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_product (product_id)
) ENGINE=InnoDB;

-- ============================================================
-- 5. WORKFLOW STEPS TABLE
-- ============================================================
CREATE TABLE workflow_steps (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    product_id VARCHAR(36) NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_order INT NOT NULL,
    description TEXT,
    duration_days INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product_order (product_id, step_order),
    UNIQUE KEY unique_product_step (product_id, step_order)
) ENGINE=InnoDB;

-- ============================================================
-- 6. DOCUMENT REQUIREMENTS TABLE (Per Workflow Step)
-- ============================================================
CREATE TABLE document_requirements (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    workflow_step_id VARCHAR(36) NOT NULL,
    doc_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_mandatory BOOLEAN DEFAULT TRUE,
    has_expiry BOOLEAN DEFAULT FALSE,
    validity_months INT,
    doc_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (workflow_step_id) REFERENCES workflow_steps(id) ON DELETE CASCADE,
    INDEX idx_workflow_step (workflow_step_id)
) ENGINE=InnoDB;

-- ============================================================
-- 7. SALES TABLE
-- ============================================================
CREATE TABLE sales (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    partner_id VARCHAR(36) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_email VARCHAR(255) NOT NULL,
    client_mobile VARCHAR(20),
    product_id VARCHAR(36) NOT NULL,
    fee_amount DECIMAL(12,2) NOT NULL,
    amount_received DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    payment_method ENUM('cash', 'bank_transfer', 'card', 'cheque', 'upi', 'other') DEFAULT 'bank_transfer',
    payment_reference VARCHAR(255),
    agreement_signed BOOLEAN DEFAULT FALSE,
    status ENUM('pending', 'approved', 'rejected', 'completed') DEFAULT 'pending',
    commission_rate DECIMAL(5,2),
    commission_amount DECIMAL(12,2),
    approved_by VARCHAR(36),
    approved_at TIMESTAMP NULL,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_partner (partner_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- 8. SALE DOCUMENTS TABLE
-- ============================================================
CREATE TABLE sale_documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    sale_id VARCHAR(36) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INT,
    content_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    INDEX idx_sale (sale_id)
) ENGINE=InnoDB;

-- ============================================================
-- 9. CASES TABLE
-- ============================================================
CREATE TABLE cases (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_id VARCHAR(50) NOT NULL UNIQUE,
    sale_id VARCHAR(36),
    client_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    case_manager_id VARCHAR(36),
    partner_id VARCHAR(36),
    status ENUM('active', 'in_progress', 'on_hold', 'completed', 'cancelled') DEFAULT 'active',
    current_step VARCHAR(255),
    current_step_order INT DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE SET NULL,
    FOREIGN KEY (client_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    FOREIGN KEY (case_manager_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_client (client_id),
    INDEX idx_case_manager (case_manager_id),
    INDEX idx_status (status),
    INDEX idx_case_id (case_id)
) ENGINE=InnoDB;

-- ============================================================
-- 10. CASE STEPS TABLE (Instance of workflow steps for each case)
-- ============================================================
CREATE TABLE case_steps (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_id VARCHAR(36) NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_order INT NOT NULL,
    status ENUM('locked', 'pending', 'in_progress', 'completed') DEFAULT 'locked',
    notes TEXT,
    is_locked BOOLEAN DEFAULT TRUE,
    approved_by VARCHAR(36),
    approved_at TIMESTAMP NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_case (case_id),
    INDEX idx_status (status),
    UNIQUE KEY unique_case_step (case_id, step_order)
) ENGINE=InnoDB;

-- ============================================================
-- 11. CASE STEP REQUIREMENTS TABLE
-- ============================================================
CREATE TABLE case_step_requirements (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_step_id VARCHAR(36) NOT NULL,
    doc_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_mandatory BOOLEAN DEFAULT TRUE,
    has_expiry BOOLEAN DEFAULT FALSE,
    expiry_date DATE,
    validity_months INT,
    doc_type VARCHAR(100),
    status ENUM('pending', 'uploaded', 'approved', 'rejected') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_step_id) REFERENCES case_steps(id) ON DELETE CASCADE,
    INDEX idx_case_step (case_step_id)
) ENGINE=InnoDB;

-- ============================================================
-- 12. DOCUMENTS TABLE (Uploaded documents)
-- ============================================================
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_id VARCHAR(36) NOT NULL,
    case_step_id VARCHAR(36),
    requirement_id VARCHAR(36),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    file_size INT,
    content_type VARCHAR(100),
    document_type VARCHAR(100),
    step_name VARCHAR(255),
    status ENUM('pending', 'uploaded', 'pending_review', 'approved', 'rejected') DEFAULT 'uploaded',
    uploaded_by VARCHAR(36) NOT NULL,
    reviewed_by VARCHAR(36),
    review_comment TEXT,
    expiry_date DATE,
    reviewed_at TIMESTAMP NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (case_step_id) REFERENCES case_steps(id) ON DELETE SET NULL,
    FOREIGN KEY (requirement_id) REFERENCES case_step_requirements(id) ON DELETE SET NULL,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_case (case_id),
    INDEX idx_status (status),
    INDEX idx_expiry (expiry_date)
) ENGINE=InnoDB;

-- ============================================================
-- 13. ADDITIONAL DOCUMENT REQUESTS TABLE
-- ============================================================
CREATE TABLE additional_doc_requests (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_id VARCHAR(36) NOT NULL,
    step_order INT,
    document_name VARCHAR(255) NOT NULL,
    description TEXT,
    due_date DATE,
    expiry_date DATE,
    validity_months INT,
    doc_type VARCHAR(100),
    status ENUM('pending', 'uploaded', 'approved', 'rejected') DEFAULT 'pending',
    requested_by VARCHAR(36) NOT NULL,
    uploaded_document_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (uploaded_document_id) REFERENCES documents(id) ON DELETE SET NULL,
    INDEX idx_case (case_id),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- ============================================================
-- 14. TICKETS TABLE
-- ============================================================
CREATE TABLE tickets (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    case_id VARCHAR(36),
    created_by VARCHAR(36) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    category ENUM('general', 'technical', 'document', 'payment', 'complaint', 'other') DEFAULT 'general',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    description TEXT NOT NULL,
    status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    target_role VARCHAR(50),
    resolution_note TEXT,
    resolved_by VARCHAR(36),
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_created_by (created_by),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
) ENGINE=InnoDB;

-- ============================================================
-- 15. TICKET TARGET USERS TABLE (Many-to-many)
-- ============================================================
CREATE TABLE ticket_targets (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    ticket_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_ticket_user (ticket_id, user_id),
    INDEX idx_ticket (ticket_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB;

-- ============================================================
-- 16. TICKET MESSAGES TABLE
-- ============================================================
CREATE TABLE ticket_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    ticket_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    INDEX idx_ticket (ticket_id)
) ENGINE=InnoDB;

-- ============================================================
-- 17. TICKET ATTACHMENTS TABLE
-- ============================================================
CREATE TABLE ticket_attachments (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    ticket_id VARCHAR(36) NOT NULL,
    uploaded_by VARCHAR(36) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INT,
    content_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE RESTRICT,
    INDEX idx_ticket (ticket_id)
) ENGINE=InnoDB;

-- ============================================================
-- 18. TICKET ACTIVITY LOG TABLE
-- ============================================================
CREATE TABLE ticket_activity_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    ticket_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_ticket (ticket_id)
) ENGINE=InnoDB;

-- ============================================================
-- 19. NOTIFICATIONS TABLE
-- ============================================================
CREATE TABLE notifications (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(100) NOT NULL,
    related_id VARCHAR(36),
    related_type VARCHAR(50),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_is_read (is_read),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- 20. PUSH SUBSCRIPTIONS TABLE
-- ============================================================
CREATE TABLE push_subscriptions (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36) NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh_key VARCHAR(500),
    auth_key VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id)
) ENGINE=InnoDB;

-- ============================================================
-- 21. SYSTEM SETTINGS TABLE
-- ============================================================
CREATE TABLE system_settings (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type ENUM('boolean', 'string', 'number', 'json') DEFAULT 'string',
    description TEXT,
    updated_by VARCHAR(36),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_key (setting_key)
) ENGINE=InnoDB;

-- ============================================================
-- 22. EXPIRY NOTIFICATIONS SENT TABLE (Track sent reminders)
-- ============================================================
CREATE TABLE expiry_notifications_sent (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    document_id VARCHAR(36) NOT NULL,
    notification_type ENUM('30_days', '15_days', '7_days', 'expired') NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE KEY unique_doc_type (document_id, notification_type),
    INDEX idx_document (document_id)
) ENGINE=InnoDB;

-- ============================================================
-- 23. AUDIT LOG TABLE (For tracking important changes)
-- ============================================================
CREATE TABLE audit_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(36),
    old_value JSON,
    new_value JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ============================================================
-- INSERT DEFAULT DATA
-- ============================================================

-- Default Admin User (Password: Admin@123)
INSERT INTO users (id, email, password, name, role, status) VALUES
('admin001', 'admin@leamss.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.NlQJYJBKZJL.4W', 'Admin User', 'admin', 'active');

-- Default Case Manager (Password: Manager@123)
INSERT INTO users (id, email, password, name, role, status) VALUES
('manager001', 'manager@leamss.com', '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Case Manager', 'case_manager', 'active');

-- Default Partner (Password: Partner@123)
INSERT INTO users (id, email, password, name, role, status, commission_rate) VALUES
('partner001', 'partner@leamss.com', '$2b$12$vE9sJTPCq0K5BnJBQPHXdOJm8dT.1CyZJY3LzOGKn5S5R5s5v5v5v', 'Partner User', 'partner', 'active', 10.00);

-- Default Client (Password: Client@123)
INSERT INTO users (id, email, password, name, role, status) VALUES
('client001', 'client@leamss.com', '$2b$12$client.hash.placeholder.here.should.be.generated', 'Client User', 'client', 'active');

-- Default System Settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('allow_case_manager_workflow_customization', 'true', 'boolean', 'Allow case managers to customize workflow steps');

-- Sample Product
INSERT INTO products (id, name, description, fee, commission_rate, commission_type) VALUES
('prod001', 'Australia PR - Permanent Residency', 'Complete assistance for Australia Permanent Residency visa application', 150000.00, 10.00, 'percentage');

-- Sample Workflow Steps for the product
INSERT INTO workflow_steps (id, product_id, step_name, step_order, description, duration_days) VALUES
('step001', 'prod001', 'Registration', 1, 'Initial registration and document collection', 7),
('step002', 'prod001', 'Document Collection', 2, 'Collect all required documents', 14),
('step003', 'prod001', 'Skills Assessment', 3, 'Skills assessment submission', 30),
('step004', 'prod001', 'EOI Submission', 4, 'Expression of Interest submission', 7),
('step005', 'prod001', 'ITA Received', 5, 'Invitation to Apply received', 60),
('step006', 'prod001', 'Visa Application', 6, 'Final visa application submission', 14),
('step007', 'prod001', 'Medical & PCC', 7, 'Medical examination and Police Clearance', 21),
('step008', 'prod001', 'Visa Grant', 8, 'Visa granted', 90);

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- View: Active Cases with Details
CREATE VIEW vw_active_cases AS
SELECT 
    c.id,
    c.case_id,
    c.status,
    c.current_step,
    c.created_at,
    cl.name AS client_name,
    cl.email AS client_email,
    cm.name AS case_manager_name,
    p.name AS product_name,
    pr.name AS partner_name
FROM cases c
JOIN users cl ON c.client_id = cl.id
LEFT JOIN users cm ON c.case_manager_id = cm.id
JOIN products p ON c.product_id = p.id
LEFT JOIN users pr ON c.partner_id = pr.id
WHERE c.status IN ('active', 'in_progress');

-- View: Pending Reviews
CREATE VIEW vw_pending_reviews AS
SELECT 
    d.id,
    d.filename,
    d.status,
    d.uploaded_at,
    d.document_type,
    c.case_id,
    u.name AS client_name,
    cm.name AS case_manager_name
FROM documents d
JOIN cases c ON d.case_id = c.id
JOIN users u ON c.client_id = u.id
LEFT JOIN users cm ON c.case_manager_id = cm.id
WHERE d.status IN ('uploaded', 'pending', 'pending_review');

-- View: Partner Sales Summary
CREATE VIEW vw_partner_sales AS
SELECT 
    u.id AS partner_id,
    u.name AS partner_name,
    COUNT(s.id) AS total_sales,
    SUM(CASE WHEN s.status = 'approved' THEN 1 ELSE 0 END) AS approved_sales,
    SUM(CASE WHEN s.status = 'pending' THEN 1 ELSE 0 END) AS pending_sales,
    SUM(CASE WHEN s.status = 'approved' THEN s.commission_amount ELSE 0 END) AS total_commission
FROM users u
LEFT JOIN sales s ON u.id = s.partner_id
WHERE u.role = 'partner'
GROUP BY u.id, u.name;

-- ============================================================
-- STORED PROCEDURES
-- ============================================================

DELIMITER //

-- Procedure: Create Case from Approved Sale
CREATE PROCEDURE sp_create_case_from_sale(
    IN p_sale_id VARCHAR(36),
    IN p_case_manager_id VARCHAR(36)
)
BEGIN
    DECLARE v_case_id VARCHAR(36);
    DECLARE v_case_number VARCHAR(50);
    DECLARE v_client_id VARCHAR(36);
    DECLARE v_product_id VARCHAR(36);
    DECLARE v_partner_id VARCHAR(36);
    DECLARE v_client_email VARCHAR(255);
    DECLARE v_client_name VARCHAR(255);
    DECLARE v_first_step VARCHAR(255);
    
    -- Get sale details
    SELECT s.product_id, s.partner_id, s.client_email, s.client_name
    INTO v_product_id, v_partner_id, v_client_email, v_client_name
    FROM sales s WHERE s.id = p_sale_id;
    
    -- Create or get client user
    SELECT id INTO v_client_id FROM users WHERE email = v_client_email LIMIT 1;
    
    IF v_client_id IS NULL THEN
        SET v_client_id = UUID();
        INSERT INTO users (id, email, password, name, role, status)
        VALUES (v_client_id, v_client_email, '$2b$12$defaultpasswordhash', v_client_name, 'client', 'active');
    END IF;
    
    -- Generate case number
    SET v_case_number = CONCAT('CASE-', DATE_FORMAT(NOW(), '%Y%m%d'), '-', LPAD(FLOOR(RAND() * 10000), 4, '0'));
    
    -- Get first step name
    SELECT step_name INTO v_first_step FROM workflow_steps 
    WHERE product_id = v_product_id ORDER BY step_order LIMIT 1;
    
    -- Create case
    SET v_case_id = UUID();
    INSERT INTO cases (id, case_id, sale_id, client_id, product_id, case_manager_id, partner_id, status, current_step, current_step_order)
    VALUES (v_case_id, v_case_number, p_sale_id, v_client_id, v_product_id, p_case_manager_id, v_partner_id, 'active', v_first_step, 1);
    
    -- Create case steps from workflow
    INSERT INTO case_steps (id, case_id, step_name, step_order, status, is_locked)
    SELECT UUID(), v_case_id, step_name, step_order, 
           CASE WHEN step_order = 1 THEN 'pending' ELSE 'locked' END,
           CASE WHEN step_order = 1 THEN FALSE ELSE TRUE END
    FROM workflow_steps WHERE product_id = v_product_id ORDER BY step_order;
    
    -- Update sale status
    UPDATE sales SET status = 'approved', approved_by = p_case_manager_id, approved_at = NOW() WHERE id = p_sale_id;
    
    SELECT v_case_id AS case_id, v_case_number AS case_number;
END //

-- Procedure: Update Case Step Status
CREATE PROCEDURE sp_update_case_step(
    IN p_case_id VARCHAR(36),
    IN p_step_order INT,
    IN p_status VARCHAR(50),
    IN p_user_id VARCHAR(36)
)
BEGIN
    -- Update current step
    UPDATE case_steps 
    SET status = p_status,
        is_locked = FALSE,
        approved_by = CASE WHEN p_status = 'completed' THEN p_user_id ELSE approved_by END,
        approved_at = CASE WHEN p_status = 'completed' THEN NOW() ELSE approved_at END,
        started_at = CASE WHEN p_status = 'in_progress' AND started_at IS NULL THEN NOW() ELSE started_at END,
        completed_at = CASE WHEN p_status = 'completed' THEN NOW() ELSE completed_at END
    WHERE case_id = p_case_id AND step_order = p_step_order;
    
    -- If completed, unlock next step
    IF p_status = 'completed' THEN
        UPDATE case_steps 
        SET is_locked = FALSE, status = 'pending'
        WHERE case_id = p_case_id AND step_order = p_step_order + 1;
        
        -- Update case current step
        UPDATE cases c
        SET current_step = (SELECT step_name FROM case_steps WHERE case_id = p_case_id AND step_order = p_step_order + 1),
            current_step_order = p_step_order + 1
        WHERE c.id = p_case_id;
    END IF;
END //

DELIMITER ;

-- ============================================================
-- TRIGGERS
-- ============================================================

DELIMITER //

-- Trigger: Auto-calculate commission on sale approval
CREATE TRIGGER trg_calculate_commission
BEFORE UPDATE ON sales
FOR EACH ROW
BEGIN
    IF NEW.status = 'approved' AND OLD.status != 'approved' THEN
        SET NEW.commission_amount = NEW.fee_amount * (NEW.commission_rate / 100);
    END IF;
END //

-- Trigger: Create notification on document upload
CREATE TRIGGER trg_notify_document_upload
AFTER INSERT ON documents
FOR EACH ROW
BEGIN
    DECLARE v_case_manager_id VARCHAR(36);
    
    SELECT case_manager_id INTO v_case_manager_id FROM cases WHERE id = NEW.case_id;
    
    IF v_case_manager_id IS NOT NULL THEN
        INSERT INTO notifications (id, user_id, title, message, type, related_id, related_type)
        VALUES (UUID(), v_case_manager_id, 'New Document Uploaded', 
                CONCAT('A new document "', NEW.filename, '" has been uploaded for review.'),
                'document_upload', NEW.id, 'document');
    END IF;
END //

DELIMITER ;

-- ============================================================
-- GRANTS (Adjust as needed for your MySQL user)
-- ============================================================
-- GRANT ALL PRIVILEGES ON leamss_portal.* TO 'your_app_user'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================================
-- END OF SCHEMA
-- ============================================================
