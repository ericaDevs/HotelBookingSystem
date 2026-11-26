from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Reservations.models import Guests
from .models import RoomImage, Rooms


class RoomDetailsTests(TestCase):
    def setUp(self):
        self.room = Rooms.objects.create(
            room_number=18,
            room_type='Garden suite',
            price=Decimal('12500.00'),
        )

    def test_room_details_displays_information_six_images_and_booking_cta(self):
        for position in range(6):
            RoomImage.objects.create(
                room=self.room,
                image=f'room_images/room-{position}.jpg',
                position=position,
            )

        response = self.client.get(reverse('per_room', args=[self.room.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Room 18')
        self.assertContains(response, 'Garden suite')
        self.assertContains(response, 'KES 12500.00')
        self.assertContains(
            response,
            f'href="{reverse("bookings")}?room={self.room.pk}"',
        )
        self.assertEqual(response.context['room'].images.count(), 6)

    def test_unavailable_room_does_not_offer_booking(self):
        self.room.is_available = False
        self.room.save(update_fields=['is_available'])

        response = self.client.get(reverse('per_room', args=[self.room.pk]))

        self.assertContains(response, 'Unavailable today')
        self.assertContains(response, 'Not available to book')
        self.assertNotContains(
            response,
            f'href="{reverse("bookings")}?room={self.room.pk}"',
        )

    def test_public_and_staff_room_lists_link_to_room_details(self):
        for url in (reverse('rooms'), reverse('staff:rooms')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    f'href="{reverse("per_room", args=[self.room.pk])}"',
                )

    def test_public_room_list_shows_current_occupied_and_unavailable_states(self):
        unavailable = Rooms.objects.create(
            room_number=19,
            room_type='Family room',
            price=Decimal('15000.00'),
            is_available=False,
        )
        today = timezone.localdate()
        Guests.objects.create(
            full_name='Current Guest',
            Id_no='ID-190',
            email='current.room.guest@example.com',
            phone_number='0712345678',
            county_of_origin='Kitui',
            country='Kenya',
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            room=self.room,
        )

        response = self.client.get(reverse('rooms'))

        self.assertContains(response, 'Occupied')
        self.assertContains(response, 'Unavailable')
        self.assertContains(response, self.room.room_type)
        self.assertContains(response, unavailable.room_type)

    def test_room_details_uses_room_type_as_name_and_shows_current_status(self):
        response = self.client.get(reverse('per_room', args=[self.room.pk]))

        self.assertContains(response, '<h1>Garden suite</h1>', html=True)
        self.assertContains(response, 'Available today')
