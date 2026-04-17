from django.test import TestCase, Client
from django.urls import reverse
from .models import Employee, Department, JobPosition
from sakinafinance.accounts.models import Company
from .forms import EmployeeForm
import uuid

class HRFormsTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.department = Department.objects.create(name="IT", company=self.company)
        self.position = JobPosition.objects.create(title="Developer", company=self.company, department=self.department)
        
    def test_employee_form_valid(self):
        form_data = {
            'employee_number': 'EMP001',
            'gender': 'M',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '123456789',
            'department': self.department.id,
            'position': self.position.id,
            'contract_type': 'cdi',
            'hire_date': '2023-01-01',
            'base_salary': 500000,
            'currency': 'XOF',
            'nationality': 'Sénégalaise',
            'national_id': '1234567890',
            'bank_name': 'Test Bank',
            'iban': 'SN12345',
            'cnss_number': 'CNSS123',
            'tax_id': 'TIN123'
        }
        form = EmployeeForm(data=form_data, company=self.company)
        self.assertTrue(form.is_valid(), form.errors)

class HRAPITestCase(TestCase):
    def setUp(self):
        # Create a user with a company
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(email='testuser@example.com', password='password')
        self.company = Company.objects.create(name="Test Company")
        self.user.company = self.company
        self.user.save()
        
        self.department = Department.objects.create(name="IT", company=self.company)
        self.position = JobPosition.objects.create(title="Developer", company=self.company, department=self.department)
        
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
    def test_api_hr_employee_add(self):
        url = reverse('api_hr_employee_add')
        data = {
            'employee_number': 'EMP002',
            'gender': 'F',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane@example.com',
            'phone': '987654321',
            'department': self.department.id,
            'position': self.position.id,
            'contract_type': 'cdi',
            'hire_date': '2023-02-01',
            'base_salary': 600000,
            'currency': 'XOF',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(Employee.objects.filter(employee_number='EMP002').exists())
