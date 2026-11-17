from datetime import date
from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase
from django.urls import reverse

from Billing.models import Payments
from Properties.models import Rooms
from Reservations.models import Guests
from Staff.models import Users


class AdminPortalPageTests(TestCase):
    def test_admin_login_page_renders(self):
        response = self.client.get(reverse('admin_portal:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'Team portal')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="role"')
        self.assertContains(response, 'name="password"')

    def test_admin_login_authenticates_and_redirects_by_role(self):
        admin = Users.objects.create(
            fullname='Portal Admin',
            username='portal-admin',
            email='admin@example.com',
            phone='0712345678',
            role='Admin',
            password=make_password('admin-pass-123'),
        )
        response = self.client.post(reverse('admin_portal:login'), {
            'username': 'portal-admin',
            'role': 'Admin',
            'password': 'admin-pass-123',
        })

        self.assertRedirects(response, reverse('admin_portal:overview'))
        self.assertEqual(self.client.session['admin_user_id'], admin.pk)

    def test_staff_login_authenticates_and_rejects_admin_role_mismatch(self):
        staff_member = Users.objects.create(
            fullname='Portal Staff',
            username='portal-staff',
            email='staff@example.com',
            phone='0712345678',
            role='Front desk',
            password=make_password('staff-pass-123'),
        )
        response = self.client.post(reverse('admin_portal:login'), {
            'username': 'portal-staff',
            'role': 'Staff',
            'password': 'staff-pass-123',
        })

        self.assertRedirects(response, reverse('staff:dashboard'))
        self.assertEqual(self.client.session['staff_user_id'], staff_member.pk)

        response = self.client.post(reverse('admin_portal:login'), {
            'username': 'portal-staff',
            'role': 'Admin',
            'password': 'staff-pass-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('admin_user_id', self.client.session)

    def test_staff_login_redirects_to_shared_login(self):
        response = self.client.get(reverse('staff:login'))

        self.assertRedirects(response, reverse('admin_portal:login'))

    def test_admin_dashboard_renders(self):
        response = self.client.get(reverse('admin_portal:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent reservations')
        self.assertContains(response, 'Hotel performance summary')

    def test_management_pages_render(self):
        for page in ('reservations', 'rooms', 'staff', 'revenue'):
            with self.subTest(page=page):
                response = self.client.get(reverse(f'admin_portal:{page}'))
                self.assertEqual(response.status_code, 200)

    def test_room_crud(self):
        url = reverse('admin_portal:rooms')
        response = self.client.post(url, {
            'action': 'create_room',
            'room_number': '12',
            'room_type': 'Garden suite',
            'price': '12500.00',
            'is_available': 'on',
        })
        self.assertRedirects(response, url)
        room = Rooms.objects.get(room_number=12)
        self.assertEqual(room.price, Decimal('12500.00'))

        self.client.post(url, {
            'action': 'update_room',
            'room_id': room.pk,
            'room_number': '12',
            'room_type': 'Deluxe suite',
            'price': '15000.00',
            'is_available': 'on',
        })
        room.refresh_from_db()
        self.assertEqual(room.room_type, 'Deluxe suite')

        self.client.post(url, {'action': 'delete_room', 'room_id': room.pk})
        self.assertFalse(Rooms.objects.filter(pk=room.pk).exists())

    def test_reservation_create_links_room_and_rejects_overlaps(self):
        room = Rooms.objects.create(
            room_number=3,
            room_type='Garden room',
            price=Decimal('8000.00'),
        )
        url = reverse('admin_portal:reservations')
        payload = {
            'action': 'create_reservation',
            'full_name': 'Test Guest',
            'email': 'guest@example.com',
            'phone_number': '0712345678',
            'id_no': 'A123456',
            'county_of_origin': 'Kitui',
            'country': 'Kenya',
            'check_in_date': '2026-12-01',
            'check_out_date': '2026-12-04',
            'room': room.pk,
        }
        response = self.client.post(url, payload)
        self.assertRedirects(response, url)
        reservation = Guests.objects.get(email='guest@example.com')
        self.assertEqual(reservation.room, room)

        payload.update({
            'email': 'other@example.com',
            'check_in_date': '2026-12-02',
            'check_out_date': '2026-12-05',
        })
        self.client.post(url, payload)
        self.assertFalse(Guests.objects.filter(email='other@example.com').exists())

    def test_staff_crud_hashes_password(self):
        url = reverse('admin_portal:staff')
        response = self.client.post(url, {
            'action': 'create_staff',
            'fullname': 'Taylor Staff',
            'username': 'taylor',
            'email': 'taylor@example.com',
            'phone': '0712345678',
            'role': 'Front desk',
            'password': 'test-pass-123',
        })
        self.assertRedirects(response, url)
        member = Users.objects.get(username='taylor')
        self.assertTrue(check_password('test-pass-123', member.password))
        self.assertNotEqual(member.password, 'test-pass-123')

        self.client.post(url, {
            'action': 'delete_staff',
            'staff_id': member.pk,
        })
        self.assertFalse(Users.objects.filter(pk=member.pk).exists())

    def test_revenue_separates_room_and_food_payments(self):
        room = Rooms.objects.create(
            room_number=22,
            room_type='Suite',
            price=Decimal('10000.00'),
        )
        guest = Guests.objects.create(
            full_name='Payment Guest',
            Id_no='ID22',
            email='payment@example.com',
            phone_number='0711111111',
            county_of_origin='Kitui',
            country='Kenya',
            check_in_date=date(2026, 12, 1),
            check_out_date=date(2026, 12, 2),
            room=room,
        )
        Payments.objects.create(
            guest=guest,
            phone_number='0711111111',
            amount=Decimal('10000.00'),
            payment_method='M-Pesa',
            category='room',
        )
        Payments.objects.create(
            guest=guest,
            phone_number='0711111111',
            amount=Decimal('1500.00'),
            payment_method='Cash',
            category='food',
        )

        response = self.client.get(reverse('admin_portal:revenue'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['room_revenue'], Decimal('10000.00'))
        self.assertEqual(response.context['food_revenue'], Decimal('1500.00'))

        rooms_response = self.client.get(reverse('admin_portal:rooms'))
        room_row = rooms_response.context['rooms'].get(pk=room.pk)
        self.assertEqual(room_row.room_revenue, Decimal('10000.00'))
