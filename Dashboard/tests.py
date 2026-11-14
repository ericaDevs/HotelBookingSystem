from django.test import TestCase
from django.urls import reverse


class DashboardPageTests(TestCase):
    def test_admin_dashboard_renders(self):
        response = self.client.get(reverse('dashboard:admin_overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent reservations')
        self.assertContains(response, 'Hotel performance summary')

    def test_agent_dashboard_renders(self):
        response = self.client.get(reverse('dashboard:agent_overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's guest schedule")
        self.assertContains(response, 'Your daily summary')
