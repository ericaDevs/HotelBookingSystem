from django.test import TestCase
from django.urls import reverse


class AdminPortalPageTests(TestCase):
    def test_admin_login_page_renders(self):
        response = self.client.get(reverse('admin_portal:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'Administrator portal')

    def test_admin_dashboard_renders(self):
        response = self.client.get(reverse('admin_portal:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent reservations')
        self.assertContains(response, 'Hotel performance summary')
