from django.test import TestCase
from django.urls import reverse


class PortalLoginPageTests(TestCase):
    def test_admin_login_page_renders(self):
        response = self.client.get(reverse('accounts:admin_login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'Administrator portal')

    def test_agent_login_page_renders(self):
        response = self.client.get(reverse('accounts:agent_login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Good to see you')
        self.assertContains(response, 'Agent workspace')
