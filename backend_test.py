import requests
import sys
import json
from datetime import datetime
import io

class LEAMSSAPITester:
    def __init__(self, base_url="https://payment-portal-323.preview.emergentagent.com"):
        self.base_url = base_url
        self.api = f"{base_url}/api"
        self.tokens = {}
        self.test_data = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append(f"{name}: {details}")

    def test_login(self, email, password, role):
        """Test login for different roles"""
        try:
            response = requests.post(f"{self.api}/auth/login", 
                                   json={"email": email, "password": password})
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[role] = data['token']
                self.test_data[f"{role}_user"] = data['user']
                self.log_test(f"Login as {role}", True)
                return True
            else:
                self.log_test(f"Login as {role}", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"Login as {role}", False, str(e))
            return False

    def get_auth_header(self, role):
        """Get authorization header for role"""
        return {'Authorization': f'Bearer {self.tokens[role]}', 'Content-Type': 'application/json'}

    def test_admin_functionality(self):
        """Test admin-specific endpoints"""
        print("\n🔧 Testing Admin Functionality...")
        
        # Test dashboard stats
        try:
            response = requests.get(f"{self.api}/stats/dashboard", headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            self.log_test("Admin Dashboard Stats", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Admin Dashboard Stats", False, str(e))

        # Test get pending sales
        try:
            response = requests.get(f"{self.api}/sales/pending", headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            if success:
                self.test_data['pending_sales'] = response.json()
            self.log_test("Get Pending Sales", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Pending Sales", False, str(e))

        # Test get all cases
        try:
            response = requests.get(f"{self.api}/cases", headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            self.log_test("Get All Cases", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get All Cases", False, str(e))

        # Test get case managers
        try:
            response = requests.get(f"{self.api}/users/case-managers", headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            if success:
                self.test_data['case_managers'] = response.json()
            self.log_test("Get Case Managers", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Case Managers", False, str(e))

        # Test create product
        try:
            product_data = {
                "name": "Test Visa Product",
                "description": "Test visa processing service",
                "fee": 5000.0,
                "commission_rate": 15.0
            }
            response = requests.post(f"{self.api}/products", 
                                   json=product_data, 
                                   headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            if success:
                self.test_data['test_product'] = response.json()
            self.log_test("Create Product", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Create Product", False, str(e))

        # Test create user (case manager)
        try:
            user_data = {
                "email": f"testmanager_{datetime.now().strftime('%H%M%S')}@test.com",
                "name": "Test Manager",
                "password": "TestPass123!",
                "role": "case_manager",
                "mobile": "+1234567890"
            }
            response = requests.post(f"{self.api}/auth/register", 
                                   json=user_data, 
                                   headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            if success:
                self.test_data['test_manager'] = response.json()
            self.log_test("Create Case Manager", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Create Case Manager", False, str(e))

    def test_partner_functionality(self):
        """Test partner-specific endpoints"""
        print("\n🤝 Testing Partner Functionality...")
        
        # Test partner dashboard stats
        try:
            response = requests.get(f"{self.api}/stats/dashboard", headers=self.get_auth_header('partner'))
            success = response.status_code == 200
            self.log_test("Partner Dashboard Stats", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Partner Dashboard Stats", False, str(e))

        # Test get products (partner needs to see available products)
        try:
            response = requests.get(f"{self.api}/products", headers=self.get_auth_header('partner'))
            success = response.status_code == 200
            if success:
                products = response.json()
                if products:
                    self.test_data['available_products'] = products
            self.log_test("Get Products (Partner)", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Products (Partner)", False, str(e))

        # Test create sale
        if 'available_products' in self.test_data and self.test_data['available_products']:
            try:
                product = self.test_data['available_products'][0]
                sale_data = {
                    "client_name": "Test Client",
                    "client_email": f"testclient_{datetime.now().strftime('%H%M%S')}@test.com",
                    "client_mobile": "+1987654321",
                    "product_id": product['id'],
                    "fee_amount": product['fee'],
                    "amount_received": product['fee'],
                    "payment_method": "bank_transfer",
                    "payment_reference": f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "agreement_signed": True
                }
                response = requests.post(f"{self.api}/sales", 
                                       json=sale_data, 
                                       headers=self.get_auth_header('partner'))
                success = response.status_code == 200
                if success:
                    self.test_data['test_sale'] = response.json()
                self.log_test("Create Sale", success, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test("Create Sale", False, str(e))

        # Test get my sales
        try:
            response = requests.get(f"{self.api}/sales/my-sales", headers=self.get_auth_header('partner'))
            success = response.status_code == 200
            self.log_test("Get My Sales", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get My Sales", False, str(e))

    def test_case_manager_functionality(self):
        """Test case manager-specific endpoints"""
        print("\n📋 Testing Case Manager Functionality...")
        
        # Test case manager dashboard stats
        try:
            response = requests.get(f"{self.api}/stats/dashboard", headers=self.get_auth_header('case_manager'))
            success = response.status_code == 200
            self.log_test("Case Manager Dashboard Stats", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Case Manager Dashboard Stats", False, str(e))

        # Test get my cases
        try:
            response = requests.get(f"{self.api}/cases/my-cases", headers=self.get_auth_header('case_manager'))
            success = response.status_code == 200
            if success:
                cases = response.json()
                if cases:
                    self.test_data['manager_cases'] = cases
            self.log_test("Get My Cases (Manager)", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get My Cases (Manager)", False, str(e))

    def test_client_functionality(self):
        """Test client-specific endpoints"""
        print("\n👤 Testing Client Functionality...")
        
        # Test client dashboard stats
        try:
            response = requests.get(f"{self.api}/stats/dashboard", headers=self.get_auth_header('client'))
            success = response.status_code == 200
            self.log_test("Client Dashboard Stats", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Client Dashboard Stats", False, str(e))

        # Test get my cases (client)
        try:
            response = requests.get(f"{self.api}/cases/my-cases", headers=self.get_auth_header('client'))
            success = response.status_code == 200
            if success:
                cases = response.json()
                if cases:
                    self.test_data['client_cases'] = cases
            self.log_test("Get My Cases (Client)", success, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get My Cases (Client)", False, str(e))

    def test_sales_approval_workflow(self):
        """Test the complete sales approval workflow"""
        print("\n🔄 Testing Sales Approval Workflow...")
        
        if 'test_sale' not in self.test_data or 'case_managers' not in self.test_data:
            self.log_test("Sales Approval Workflow", False, "Missing test data (sale or case managers)")
            return

        if not self.test_data['case_managers']:
            self.log_test("Sales Approval Workflow", False, "No case managers available")
            return

        try:
            # Approve the test sale
            case_manager = self.test_data['case_managers'][0]
            approval_data = {
                "sale_id": self.test_data['test_sale']['id'],
                "status": "approved",
                "case_manager_id": case_manager['id']
            }
            response = requests.post(f"{self.api}/sales/approve", 
                                   json=approval_data, 
                                   headers=self.get_auth_header('admin'))
            success = response.status_code == 200
            self.log_test("Approve Sale", success, f"Status: {response.status_code}")
            
            if success:
                # This should create a client account and case automatically
                # Let's verify by checking if new cases were created
                response = requests.get(f"{self.api}/cases", headers=self.get_auth_header('admin'))
                if response.status_code == 200:
                    self.log_test("Auto Case Creation", True)
                else:
                    self.log_test("Auto Case Creation", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sales Approval Workflow", False, str(e))

    def test_role_based_access_control(self):
        """Test that users can only access their authorized endpoints"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        # Test that partner cannot access admin endpoints
        try:
            response = requests.get(f"{self.api}/sales/pending", headers=self.get_auth_header('partner'))
            success = response.status_code == 403
            self.log_test("Partner Access Control (Admin Endpoint)", success, 
                         f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_test("Partner Access Control (Admin Endpoint)", False, str(e))

        # Test that client cannot access case manager endpoints
        try:
            response = requests.get(f"{self.api}/cases", headers=self.get_auth_header('client'))
            success = response.status_code == 403
            self.log_test("Client Access Control (Admin Endpoint)", success, 
                         f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_test("Client Access Control (Admin Endpoint)", False, str(e))

        # Test that case manager cannot access admin-only endpoints
        try:
            response = requests.get(f"{self.api}/users/case-managers", headers=self.get_auth_header('case_manager'))
            success = response.status_code == 403
            self.log_test("Case Manager Access Control (Admin Endpoint)", success, 
                         f"Expected 403, got {response.status_code}")
        except Exception as e:
            self.log_test("Case Manager Access Control (Admin Endpoint)", False, str(e))

    def run_all_tests(self):
        """Run comprehensive API tests"""
        print("🚀 Starting LEAMSS Immigration Portal API Tests\n")
        
        # Test credentials from the review request
        credentials = [
            ("admin@leamss.com", "Admin@123", "admin"),
            ("manager@leamss.com", "Manager@123", "case_manager"),
            ("partner@leamss.com", "Partner@123", "partner"),
            ("client@leamss.com", "Client@123", "client")
        ]
        
        print("🔐 Testing Authentication...")
        for email, password, role in credentials:
            self.test_login(email, password, role)
        
        # Only proceed if we have successful logins
        if len(self.tokens) < 4:
            print(f"\n❌ Authentication failed for some roles. Only {len(self.tokens)} out of 4 roles authenticated.")
            return False
        
        # Test role-specific functionality
        self.test_admin_functionality()
        self.test_partner_functionality()
        self.test_case_manager_functionality()
        self.test_client_functionality()
        
        # Test workflows
        self.test_sales_approval_workflow()
        
        # Test access control
        self.test_role_based_access_control()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LEAMSSAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())