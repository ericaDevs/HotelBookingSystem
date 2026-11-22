from django.db.models import Avg
from django.shortcuts import redirect, render
from django.utils import timezone

from HotelSystem.views import get_contact_submissions
from Properties.models import Rooms
from Reservations.models import Guests
from Staff.models import Users


def _dashboard_context(request, active_nav):
    staff_id = request.session.get("staff_user_id")
    staff_member = (
        Users.objects.filter(pk=staff_id).first()
        if isinstance(staff_id, int)
        else None
    )
    staff_name = (
        staff_member.fullname.strip()
        if staff_member and staff_member.fullname.strip()
        else "Front Desk Team"
    )
    initials = "".join(
        word[0].upper() for word in staff_name.split()[:2]
    ) or "FD"
    return {
        "active_nav": active_nav,
        "today": timezone.localdate(),
        "staff_name": staff_name,
        "staff_role": (
            staff_member.role.strip()
            if staff_member and staff_member.role.strip()
            else "Guest Services"
        ),
        "staff_initials": initials,
    }


def _reservation_rows(today):
    rows = []
    for guest in Guests.objects.select_related("room").order_by(
        "check_in_date", "full_name", "pk"
    ):
        if guest.check_out_date <= today:
            status, status_key = "Checked out", "checked-out"
        elif guest.check_in_date <= today:
            status, status_key = "In house", "in-house"
        else:
            status, status_key = "Upcoming", "upcoming"
        rows.append({
            "guest": guest,
            "status": status,
            "status_key": status_key,
        })
    return rows


def _room_rows(today):
    occupied_guests = Guests.objects.filter(
        check_in_date__lte=today,
        check_out_date__gt=today,
        room__isnull=False,
    ).select_related("room").order_by("check_in_date", "full_name", "pk")
    occupied_by_room = {}
    for guest in occupied_guests:
        occupied_by_room.setdefault(guest.room_id, guest)

    rows = []
    for room in Rooms.objects.order_by("room_number"):
        guest = occupied_by_room.get(room.pk)
        if guest:
            status, status_key = "Occupied", "occupied"
        elif room.is_available:
            status, status_key = "Available", "available"
        else:
            status, status_key = "Unavailable", "unavailable"
        rows.append({
            "room": room,
            "guest": guest,
            "status": status,
            "status_key": status_key,
        })
    return rows


def staff_login(request):
    return redirect("admin_portal:login")


def staff_dashboard(request):
    today = timezone.localdate()
    room_rows = _room_rows(today)
    arrivals = list(
        Guests.objects.filter(check_in_date=today)
        .select_related("room")
        .order_by("full_name", "pk")
    )
    departures = list(
        Guests.objects.filter(check_out_date=today)
        .select_related("room")
        .order_by("full_name", "pk")
    )
    schedule_rows = [
        {"guest": guest, "movement": "Arrival", "movement_key": "arrival"}
        for guest in arrivals
    ] + [
        {"guest": guest, "movement": "Departure", "movement_key": "departure"}
        for guest in departures
    ]
    in_house = Guests.objects.filter(
        check_in_date__lte=today,
        check_out_date__gt=today,
    ).count()
    available_rooms = sum(row["status_key"] == "available" for row in room_rows)
    occupied_rooms = sum(row["status_key"] == "occupied" for row in room_rows)
    unavailable_rooms = sum(row["status_key"] == "unavailable" for row in room_rows)
    category_counts = {}
    for row in room_rows:
        category = row["room"].room_type
        category_counts[category] = category_counts.get(category, 0) + 1

    context = _dashboard_context(request, "dashboard")
    context.update({
        "arrivals_today": len(arrivals),
        "departures_today": len(departures),
        "in_house": in_house,
        "upcoming_reservations": Guests.objects.filter(
            check_in_date__gt=today
        ).count(),
        "schedule_rows": schedule_rows,
        "available_rooms": available_rooms,
        "occupied_rooms": occupied_rooms,
        "unavailable_rooms": unavailable_rooms,
        "room_count": len(room_rows),
        "room_preview": room_rows[:8],
        "room_categories": [
            {"name": name, "count": count}
            for name, count in sorted(category_counts.items())
        ],
    })
    return render(request, "staff_portal/overview.html", context)


def staff_reservations(request):
    today = timezone.localdate()
    reservation_rows = _reservation_rows(today)
    context = _dashboard_context(request, "reservations")
    context.update({
        "reservations": reservation_rows,
        "total_reservations": len(reservation_rows),
        "arrivals_today": Guests.objects.filter(check_in_date=today).count(),
        "departures_today": Guests.objects.filter(check_out_date=today).count(),
        "in_house": Guests.objects.filter(
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).count(),
        "upcoming": Guests.objects.filter(check_in_date__gt=today).count(),
        "checked_out": Guests.objects.filter(check_out_date__lte=today).count(),
        "search_query": request.GET.get("q", "").strip(),
    })
    return render(request, "staff_portal/reservations.html", context)


def staff_rooms(request):
    today = timezone.localdate()
    room_rows = _room_rows(today)
    category_counts = {}
    for row in room_rows:
        category = row["room"].room_type
        category_counts[category] = category_counts.get(category, 0) + 1
    context = _dashboard_context(request, "rooms")
    context.update({
        "rooms": room_rows,
        "room_count": len(room_rows),
        "available_rooms": sum(row["status_key"] == "available" for row in room_rows),
        "occupied_rooms": sum(row["status_key"] == "occupied" for row in room_rows),
        "unavailable_rooms": sum(row["status_key"] == "unavailable" for row in room_rows),
        "room_categories": [
            {"name": name, "count": count}
            for name, count in sorted(category_counts.items())
        ],
        "average_rate": Rooms.objects.aggregate(value=Avg("price"))["value"] or 0,
    })
    return render(request, "staff_portal/rooms.html", context)





def staff_contacts(request):
    today = timezone.localdate()
    contact_messages = get_contact_submissions()
    contacts = Guests.objects.select_related("room").order_by("full_name", "pk")
    contact_rows = []
    for guest in contacts:
        if guest.check_out_date <= today:
            status, status_key = "Checked out", "checked-out"
        elif guest.check_in_date <= today:
            status, status_key = "In house", "in-house"
        else:
            status, status_key = "Upcoming", "upcoming"
        contact_rows.append({
            "guest": guest,
            "status": status,
            "status_key": status_key,
        })

    context = _dashboard_context(request, "contacts")
    context.update({
        "contacts": contact_rows,
        "contact_messages": contact_messages,
        "total_messages": contact_messages.count(),
        "total_contacts": len(contact_rows),
        "in_house": Guests.objects.filter(
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).count(),
        "upcoming": Guests.objects.filter(check_in_date__gt=today).count(),
        "checked_out": Guests.objects.filter(check_out_date__lte=today).count(),
        "unassigned": Guests.objects.filter(
            room__isnull=True,
            check_out_date__gt=today,
        ).count(),
    })
    return render(request, "staff_portal/contacts.html", context)