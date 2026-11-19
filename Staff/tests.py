from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Properties.models import Rooms
from Reservations.models import Guests


class PortalLoginPageTests(TestCase):
    def test_staff_login_redirects_to_shared_login(self):
        response = self.client.get(reverse("staff:login"))

        self.assertRedirects(response, reverse("admin_portal:login"))


class StaffPortalPageTests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.room = Rooms.objects.create(
            room_number=123,
            room_type="Kings",
            price=Decimal("2000.00"),
        )
        self.unavailable_room = Rooms.objects.create(
            room_number=124,
            room_type="Garden",
            price=Decimal("3000.00"),
            is_available=False,
        )
        Rooms.objects.create(
            room_number=125,
            room_type="Suite",
            price=Decimal("5000.00"),
        )
        self.arrival = self.create_guest(
            "Arrival Guest", "arrival@example.com", today, today + timedelta(days=1), self.room
        )
        self.departure = self.create_guest(
            "Departure Guest",
            "departure@example.com",
            today - timedelta(days=1),
            today,
            self.unavailable_room,
        )
        self.upcoming = self.create_guest(
            "Future Guest",
            "future@example.com",
            today + timedelta(days=2),
            today + timedelta(days=3),
        )
        self.past = self.create_guest(
            "Past Guest",
            "past@example.com",
            today - timedelta(days=3),
            today - timedelta(days=2),
        )

    def create_guest(self, name, email, check_in, check_out, room=None):
        return Guests.objects.create(
            full_name=name,
            Id_no=f"ID-{name.split()[0]}",
            email=email,
            phone_number="0712345678",
            county_of_origin="Kitui",
            country="Kenya",
            check_in_date=check_in,
            check_out_date=check_out,
            room=room,
        )

    def test_overview_uses_live_reservation_and_room_data(self):
        response = self.client.get(reverse("staff:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's guest movement")
        self.assertContains(response, "Arrival Guest")
        self.assertContains(response, "Departure Guest")
        self.assertEqual(response.context["arrivals_today"], 1)
        self.assertEqual(response.context["departures_today"], 1)
        self.assertEqual(response.context["in_house"], 1)
        self.assertEqual(response.context["available_rooms"], 1)
        self.assertEqual(response.context["occupied_rooms"], 1)
        self.assertEqual(response.context["unavailable_rooms"], 1)

    def test_staff_modules_render_database_backed_records(self):
        pages = (
            ("staff:reservations", "Guest Reservations", "Arrival Guest"),
            ("staff:contacts", "Guest Contacts", "arrival@example.com"),
            ("staff:rooms", "Room Availability", "Room 123"),
        )
        for route, heading, record in pages:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(response, record)

    def test_global_reservation_search_is_preserved_in_reservation_module(self):
        response = self.client.get(
            reverse("staff:reservations"),
            {"q": "Arrival Guest"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Arrival Guest"')
        self.assertContains(response, "data-status=\"in-house\"", html=False)
