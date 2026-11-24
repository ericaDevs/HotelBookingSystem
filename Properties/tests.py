from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

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

        self.assertContains(response, 'Currently unavailable')
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
