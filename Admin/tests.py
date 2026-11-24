import json
from io import BytesIO
from tempfile import TemporaryDirectory
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from Billing.models import Payments
from Admin.models import Contacts
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

    def test_login_api_authenticates_staff_and_returns_named_route(self):
        staff_member = Users.objects.create(
            fullname='API Staff',
            username='api-staff',
            email='api-staff@example.com',
            phone='0712345678',
            role='Front desk',
            password=make_password('api-pass-123'),
        )
        response = self.client.post(
            reverse('admin_portal:login_api'),
            data=json.dumps({
                'username': 'api-staff',
                'role': 'Staff',
                'password': 'api-pass-123',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'success': True, 'redirect_url': reverse('staff:dashboard')},
        )
        self.assertEqual(self.client.session['staff_user_id'], staff_member.pk)

    def test_login_api_returns_json_errors_for_invalid_requests(self):
        api_url = reverse('admin_portal:login_api')
        missing_fields = self.client.post(
            api_url,
            data=json.dumps({'username': 'someone', 'role': 'Staff'}),
            content_type='application/json',
        )
        self.assertEqual(missing_fields.status_code, 400)
        self.assertIn('message', missing_fields.json())

        invalid_credentials = self.client.post(
            api_url,
            data=json.dumps({
                'username': 'missing-user',
                'role': 'Staff',
                'password': 'wrong-password',
            }),
            content_type='application/json',
        )
        self.assertEqual(invalid_credentials.status_code, 401)
        self.assertEqual(
            invalid_credentials.json()['message'],
            'Invalid username, role, or password.',
        )

        malformed_json = self.client.post(
            api_url,
            data='{',
            content_type='application/json',
        )
        self.assertEqual(malformed_json.status_code, 400)

        unsupported_method = self.client.get(api_url)
        self.assertEqual(unsupported_method.status_code, 405)

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

    def test_admin_overview_uses_live_reservation_and_room_metrics(self):
        room = Rooms.objects.create(
            room_number=41,
            room_type='Garden suite',
            price=Decimal('12000.00'),
        )
        today = timezone.localdate()
        Guests.objects.create(
            full_name='Current Guest',
            Id_no='ID41',
            email='current.guest@example.com',
            phone_number='0712345678',
            county_of_origin='Kitui',
            country='Kenya',
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            room=room,
        )

        response = self.client.get(reverse('admin_portal:overview'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['in_house_guests'], 1)
        self.assertEqual(response.context['today_arrivals'], 1)
        self.assertEqual(response.context['occupied_rooms'], 1)
        self.assertEqual(response.context['occupancy_percent'], 100)
        self.assertContains(response, 'Current Guest')
        self.assertContains(response, 'In house')

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

    def test_room_crud_accepts_text_room_number_and_two_shilling_rate(self):
        response = self.client.post(reverse('admin_portal:rooms'), {
            'action': 'create_room',
            'room_number': 'A101',
            'room_type': 'Garden suite',
            'price': '2',
            'is_available': 'on',
        })

        self.assertRedirects(response, reverse('admin_portal:rooms'))
        room = Rooms.objects.get(room_number='A101')
        self.assertEqual(room.price, Decimal('2.00'))

    def test_room_management_accepts_six_room_images(self):
        room = Rooms.objects.create(
            room_number=14,
            room_type='Garden suite',
            price=Decimal('12500.00'),
        )
        image_buffer = BytesIO()
        Image.new('RGB', (1, 1)).save(image_buffer, format='PNG')
        image_content = image_buffer.getvalue()
        uploads = [
            SimpleUploadedFile(
                f'room-{index}.png',
                image_content,
                content_type='image/png',
            )
            for index in range(6)
        ]

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('admin_portal:rooms'), {
                'action': 'update_room',
                'room_id': room.pk,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'price': str(room.price),
                'is_available': 'on',
                'room_images': uploads,
            })

        self.assertRedirects(response, reverse('admin_portal:rooms'))
        self.assertEqual(room.images.count(), 6)

    def test_room_management_rejects_non_image_uploads(self):
        room = Rooms.objects.create(
            room_number=15,
            room_type='Garden suite',
            price=Decimal('12500.00'),
        )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('admin_portal:rooms'), {
                'action': 'update_room',
                'room_id': room.pk,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'price': str(room.price),
                'is_available': 'on',
                'room_images': SimpleUploadedFile(
                    'not-an-image.png',
                    b'not an image',
                    content_type='image/png',
                ),
            })

        self.assertRedirects(response, reverse('admin_portal:rooms'))
        self.assertEqual(room.images.count(), 0)

    def test_room_bulk_availability_updates_only_selected_rooms(self):
        selected = [
            Rooms.objects.create(
                room_number=61 + index,
                room_type='Garden suite',
                price=Decimal('12000.00'),
            )
            for index in range(2)
        ]
        other = Rooms.objects.create(
            room_number=63,
            room_type='Garden suite',
            price=Decimal('12000.00'),
        )
        url = reverse('admin_portal:rooms')

        response = self.client.post(url, {
            'action': 'bulk_availability',
            'room_ids': [room.pk for room in selected],
            'bulk_availability': 'unavailable',
        })

        self.assertRedirects(response, url)
        for room in selected:
            room.refresh_from_db()
            self.assertFalse(room.is_available)
        other.refresh_from_db()
        self.assertTrue(other.is_available)

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

    def test_reservations_page_renders_filterable_guest_rows(self):
        room = Rooms.objects.create(
            room_number=55,
            room_type='Garden suite',
            price=Decimal('12000.00'),
        )
        today = timezone.localdate()
        Guests.objects.create(
            full_name='Reservation Test Guest',
            Id_no='ID55',
            email='reservation.test@example.com',
            phone_number='0712345678',
            county_of_origin='Kitui',
            country='Kenya',
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            room=room,
        )

        response = self.client.get(reverse('admin_portal:reservations'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reservation Test Guest')
        self.assertContains(response, 'data-status="in-house"')
        self.assertContains(response, 'Filter reservations by stay status')
        self.assertContains(response, 'Download Roster')

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


class ContactSubmissionTests(TestCase):
    def setUp(self):
        self.payload = {
            'full_name': '  Alex   Guest ',
            'email': 'ALEX@example.com',
            'phone_number': '+254 712 345 678',
            'inquery_type': 'rooms',
            'subject': '  Room   reservation ',
            'message': ' I would like to ask about availability. ',
        }

    def post_contact(self, payload):
        return self.client.post(
            reverse('contact'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_contact_page_renders_validation_script(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js/contacts.js')

    def test_valid_contact_json_is_cleaned_and_saved(self):
        response = self.post_contact(self.payload)

        self.assertEqual(response.status_code, 201)
        contact = Contacts.objects.get(pk=response.json()['contact_id'])
        self.assertEqual(contact.full_name, 'Alex Guest')
        self.assertEqual(contact.email, 'alex@example.com')
        self.assertEqual(contact.phone_number, '+254712345678')
        self.assertEqual(contact.subject, 'Room reservation')
        self.assertEqual(contact.message, 'I would like to ask about availability.')

    def test_invalid_phone_and_duplicate_email_are_rejected(self):
        invalid_phone = dict(self.payload, phone_number='call me')
        response = self.post_contact(invalid_phone)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.json()['errors'])

        Contacts.objects.create(
            full_name='Existing Contact',
            email='alex@example.com',
            phone_number='0712345678',
            inquery_type='rooms',
            subject='Existing request',
            message='Already sent',
        )
        response = self.post_contact(self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])
        self.assertEqual(Contacts.objects.count(), 1)
