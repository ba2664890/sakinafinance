from django.test import TestCase
from django.urls import reverse


class LegalPagesTests(TestCase):
    def test_legal_pages_are_accessible(self):
        for route_name in ('privacy', 'terms', 'cookies'):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name), follow=True)
                self.assertEqual(response.status_code, 200)

    def test_cookies_page_contains_preferences_form(self):
        response = self.client.get(reverse('cookies'), follow=True)
        self.assertContains(response, 'id="cookie-preferences-form"')
        self.assertContains(response, 'consent-analytics')
        self.assertContains(response, 'consent-marketing')
