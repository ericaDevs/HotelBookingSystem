from django.test import TestCase
from django.urls import reverse


class PortalLoginPageTests(TestCase):
    def test_staff_login_page_renders(self):
        response = self.client.get(reverse('staff:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Good to see you')

    def test_staff_dashboard_renders(self):
        response = self.client.get(reverse('staff:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's guest schedule")
