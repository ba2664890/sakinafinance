from django.test import Client, TestCase
from django.urls import reverse

from sakinafinance.accounts.models import Company, User


class AccountsSecurityTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name='Alpha')
        self.company_b = Company.objects.create(name='Beta')

    def test_business_admin_role_does_not_grant_django_superuser_rights(self):
        user = User.objects.create_user(
            email='admin@alpha.test',
            password='testpass123',
            first_name='Alpha',
            last_name='Admin',
            company=self.company_a,
            role=User.Role.ADMIN,
        )

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_users_api_is_scoped_to_authenticated_company(self):
        user_a = User.objects.create_user(
            email='user-a@alpha.test',
            password='testpass123',
            first_name='User',
            last_name='A',
            company=self.company_a,
            role=User.Role.CFO,
        )
        colleague = User.objects.create_user(
            email='user-b@alpha.test',
            password='testpass123',
            first_name='User',
            last_name='B',
            company=self.company_a,
            role=User.Role.ACCOUNTANT,
        )
        outsider = User.objects.create_user(
            email='outsider@beta.test',
            password='testpass123',
            first_name='Out',
            last_name='Sider',
            company=self.company_b,
            role=User.Role.CFO,
        )

        client = Client()
        client.force_login(user_a)
        response = client.get(reverse('user-list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        emails = {row['email'] for row in payload['results']}
        self.assertEqual(emails, {user_a.email, colleague.email})
        self.assertNotIn(outsider.email, emails)

    def test_companies_api_returns_only_current_company(self):
        user_a = User.objects.create_user(
            email='company-admin@alpha.test',
            password='testpass123',
            first_name='Company',
            last_name='Admin',
            company=self.company_a,
            role=User.Role.ADMIN,
        )

        client = Client()
        client.force_login(user_a)
        response = client.get(reverse('company-list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['results'][0]['id'], str(self.company_a.id))
