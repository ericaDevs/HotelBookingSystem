import json
from datetime import date, timedelta

from django.test import TestCase

from Properties.models import Rooms
from .models import Guests


class BookingSubmissionTests(TestCase):
    def setUp(self):
        self.room = Rooms.objects.create(
            room_number=101,
            room_type="Standard",
            price="120.00",
            is_available=True,
        )
        self.payload = {
            "full_name": "  Ada   Guest ",
            "Id_no": "ID-123",
            "email": "ADA@example.com",
            "phone_number": "+254 712 345 678",
            "county_of_origin": " Kitui ",
            "country": " Kenya ",
            "check_in_date": (date.today() + timedelta(days=1)).isoformat(),
            "check_out_date": (date.today() + timedelta(days=3)).isoformat(),
            "room": str(self.room.pk),
            "payment_method": "M-Pesa",
        }

    def post_booking(self, payload):
        return self.client.post(
            "/bookings/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_booking_page_renders_with_external_validation_script(self):
        response = self.client.get("/bookings/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "js/bookings.js")

    def test_valid_json_saves_clean_guest_record(self):
        response = self.post_booking(self.payload)

        self.assertEqual(response.status_code, 201)
        guest = Guests.objects.get(pk=response.json()["guest_id"])
        self.assertEqual(guest.full_name, "Ada Guest")
        self.assertEqual(guest.email, "ada@example.com")
        self.assertEqual(guest.phone_number, "+254712345678")
        self.assertEqual(guest.room, self.room)

    def test_invalid_stay_dates_are_rejected(self):
        self.payload["check_out_date"] = self.payload["check_in_date"]

        response = self.post_booking(self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("check_out_date", response.json()["errors"])
        self.assertEqual(Guests.objects.count(), 0)

    def test_duplicate_email_is_rejected_by_model_validation(self):
        Guests.objects.create(
            full_name="Existing Guest",
            Id_no="ID-999",
            email="ada@example.com",
            phone_number="0712345678",
            county_of_origin="Kitui",
            country="Kenya",
            check_in_date=date.today() + timedelta(days=5),
            check_out_date=date.today() + timedelta(days=7),
            room=self.room,
        )

        response = self.post_booking(self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])
        self.assertEqual(Guests.objects.count(), 1)

    def test_unavailable_room_is_rejected(self):
        self.room.is_available = False
        self.room.save(update_fields=["is_available"])

        response = self.post_booking(self.payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("room", response.json()["errors"])
        self.assertEqual(Guests.objects.count(), 0)
