from .models import Guests


def has_room_conflict(room, check_in_date, check_out_date, exclude_guest_id=None):
    reservations = Guests.objects.filter(
        room=room,
        check_in_date__lt=check_out_date,
        check_out_date__gt=check_in_date,
    )
    if exclude_guest_id is not None:
        reservations = reservations.exclude(pk=exclude_guest_id)
    return reservations.exists()


def add_current_availability(rooms, today):
    rooms = list(rooms)
    occupied_room_ids = set(
        Guests.objects.filter(
            room_id__in=[room.pk for room in rooms],
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).values_list("room_id", flat=True)
    )

    for room in rooms:
        if not room.is_available:
            room.current_status = "Unavailable"
            room.current_status_key = "unavailable"
        elif room.pk in occupied_room_ids:
            room.current_status = "Occupied"
            room.current_status_key = "occupied"
        else:
            room.current_status = "Available"
            room.current_status_key = "available"
    return rooms
