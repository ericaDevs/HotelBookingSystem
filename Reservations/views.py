import json
import re

from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from Properties.models import Rooms
from .models import Guests


def bookings(request):
    if request.method == "POST":
        if request.content_type != "application/json":
            return JsonResponse(
                {"ok": False, "errors": {"form": ["Send booking details as JSON."]}},
                status=415,
            )

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"ok": False, "errors": {"form": ["The booking data is not valid JSON."]}},
                status=400,
            )

        if not isinstance(payload, dict):
            return JsonResponse(
                {"ok": False, "errors": {"form": ["The booking data must be a JSON object."]}},
                status=400,
            )

        text_fields = (
            "full_name",
            "Id_no",
            "email",
            "phone_number",
            "county_of_origin",
            "country",
        )
        values = {}
        errors = {}
        for field in text_fields:
            value = payload.get(field)
            if not isinstance(value, str):
                errors[field] = ["This field is required."]
                continue
            value = " ".join(value.strip().split())
            if field == "email":
                value = value.lower()
            elif field == "phone_number":
                value = re.sub(r"[\s()-]", "", value)
            values[field] = value
            if not value:
                errors[field] = ["This field is required."]
            elif field == "phone_number" and not re.fullmatch(r"\+?\d{7,15}", value):
                errors[field] = ["Enter a valid phone number using 7 to 15 digits."]

        check_in = parse_date(payload.get("check_in_date", "")) if isinstance(
            payload.get("check_in_date"), str
        ) else None
        check_out = parse_date(payload.get("check_out_date", "")) if isinstance(
            payload.get("check_out_date"), str
        ) else None
        if check_in is None:
            errors["check_in_date"] = ["Enter a valid check-in date."]
        if check_out is None:
            errors["check_out_date"] = ["Enter a valid check-out date."]
        if check_in and check_out and check_out <= check_in:
            errors["check_out_date"] = ["Check-out must be after check-in."]

        room_id = payload.get("room")
        if (
            not isinstance(room_id, (str, int))
            or not str(room_id).isdecimal()
            or len(str(room_id)) > 19
            or int(room_id) > 9223372036854775807
        ):
            errors["room"] = ["Select an available room."]
            room = None
        else:
            room = Rooms.objects.filter(pk=int(room_id), is_available=True).first()
            if room is None:
                errors["room"] = ["The selected room is not available."]

        payment_method = payload.get("payment_method")
        if payment_method not in ("M-Pesa", "Pay on Arrival"):
            errors["payment_method"] = ["Select a valid payment method."]

        if errors:
            return JsonResponse({"ok": False, "errors": errors}, status=400)

        if Guests.objects.filter(email__iexact=values["email"]).exists():
            return JsonResponse(
                {"ok": False, "errors": {"email": ["A booking already uses this email address."]}},
                status=400,
            )

        guest = Guests(
            **values,
            check_in_date=check_in,
            check_out_date=check_out,
            room=room,
        )
        try:
            guest.full_clean()
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                errors = {
                    field: [str(message) for message in messages]
                    for field, messages in exc.message_dict.items()
                }
            else:
                errors = {"form": [str(message) for message in exc.messages]}
            return JsonResponse({"ok": False, "errors": errors}, status=400)

        guest.save()
        return JsonResponse(
            {
                "ok": True,
                "message": "Booking details saved.",
                "guest_id": guest.pk,
                "payment_method": payment_method,
            },
            status=201,
        )

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])

    rooms = Rooms.objects.filter(is_available=True).order_by("room_number")
    selected_room = None
    room_id = request.GET.get("room")
    if room_id:
        if not room_id.isdecimal():
            raise Http404
        selected_room = get_object_or_404(rooms, pk=int(room_id))

    return render(
        request,
        "bookings.html",
        {
            "rooms": rooms,
            "selected_room": selected_room,
        },
    )
