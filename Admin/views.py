import json
import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse

from Billing.models import Payments
from Properties.models import RoomImage, Rooms
from Reservations.models import Guests
from Staff.models import Users
from Admin.models import Contacts



# LOGIN VALIDATION VIEW
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        role = request.POST.get("role", "").strip().casefold()
        password = request.POST.get("password", "")

        if not username or role not in {"admin", "staff"} or not password:
            messages.error(request, "Enter your username, role, and password.")
        else:
            user = Users.objects.filter(username__iexact=username).first()
            admin_roles = {"admin", "administrator"}
            is_admin_user = bool(
                user and user.role.strip().casefold() in admin_roles
            )
            if (
                user
                and check_password(password, user.password)
                and ((role == "admin") == is_admin_user)
            ):
                request.session.pop("admin_user_id", None)
                request.session.pop("staff_user_id", None)
                if role == "admin":
                    request.session["admin_user_id"] = user.id
                    destination = "admin_portal:overview"
                else:
                    request.session["staff_user_id"] = user.id
                    destination = "staff:dashboard"
                messages.success(request, f"Welcome back, {user.fullname}!")
                return redirect(destination)
            else:
                messages.error(request, "Invalid username, role, or password.")
        
    return render(request, 'auth/login.html')


def admin_logout(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    request.session.pop("admin_user_id", None)
    request.session.pop("staff_user_id", None)
    request.session.cycle_key()
    return redirect("admin_portal:login")


# API END-POINT VIEW
def api_endpoint(request):
    if request.method != "POST":
        response = JsonResponse(
            {"success": False, "message": "Only POST requests are allowed."},
            status=405,
        )
        response["Allow"] = "POST"
        return response

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "Request body must contain valid JSON."},
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {"success": False, "message": "Request body must be a JSON object."},
            status=400,
        )

    username = payload.get("username")
    role = payload.get("role")
    password = payload.get("password")
    if not all(isinstance(value, str) for value in (username, role, password)):
        return JsonResponse(
            {
                "success": False,
                "message": "Username, role, and password are required.",
            },
            status=400,
        )

    username = username.strip()
    role = role.strip().casefold()
    if not username or role not in {"admin", "staff"} or not password:
        return JsonResponse(
            {
                "success": False,
                "message": "Enter your username, role, and password.",
            },
            status=400,
        )

    user = Users.objects.filter(username__iexact=username).first()
    admin_roles = {"admin", "administrator"}
    is_admin_user = bool(user and user.role.strip().casefold() in admin_roles)
    if (
        not user
        or not check_password(password, user.password)
        or ((role == "admin") != is_admin_user)
    ):
        return JsonResponse(
            {"success": False, "message": "Invalid username, role, or password."},
            status=401,
        )

    request.session.pop("admin_user_id", None)
    request.session.pop("staff_user_id", None)
    request.session.cycle_key()
    if role == "admin":
        request.session["admin_user_id"] = user.id
        destination = "admin_portal:overview"
    else:
        request.session["staff_user_id"] = user.id
        destination = "staff:dashboard"

    return JsonResponse(
        {
            "success": True,
            "redirect_url": reverse(destination),
        }
    )



# DASHBOARD OVERVIEW VIEW
def overview(request):
    today = timezone.localdate()
    in_house = Guests.objects.filter(
        check_in_date__lte=today,
        check_out_date__gt=today,
    )
    room_count = Rooms.objects.count()
    occupied_rooms = Rooms.objects.filter(
        reservations__check_in_date__lte=today,
        reservations__check_out_date__gt=today,
    ).distinct().count()
    room_categories = Rooms.objects.values('room_type').annotate(
        total=Count('pk'),
        occupied=Count(
            'reservations',
            filter=Q(
                reservations__check_in_date__lte=today,
                reservations__check_out_date__gt=today,
            ),
            distinct=True,
        ),
    ).order_by('room_type')
    room_categories = [
        {
            **category,
            'available': category['total'] - category['occupied'],
            'occupancy_percent': round(
                category['occupied'] / category['total'] * 100
            ) if category['total'] else 0,
        }
        for category in room_categories
    ]
    recent_reservations = Guests.objects.select_related('room').order_by('-pk')[:5]
    recent_payments = Payments.objects.filter(
        payment_date__date=today
    ).select_related('guest').order_by('-payment_date')[:5]
    staff_members = Users.objects.exclude(
        role__iexact='admin'
    ).exclude(
        role__iexact='administrator'
    ).order_by('fullname')[:3]
    today_revenue = Payments.objects.filter(
        payment_date__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return render(request, 'admin_portal/overview.html', {
        'today': today,
        'in_house_guests': in_house.count(),
        'today_arrivals': Guests.objects.filter(check_in_date=today).count(),
        'today_departures': Guests.objects.filter(check_out_date=today).count(),
        'room_count': room_count,
        'occupied_rooms': occupied_rooms,
        'available_rooms': room_count - occupied_rooms,
        'occupancy_percent': round(occupied_rooms / room_count * 100) if room_count else 0,
        'today_revenue': today_revenue,
        'recent_reservations': recent_reservations,
        'recent_payments': recent_payments,
        'room_categories': room_categories,
        'staff_members': staff_members,
    })



# RESERVATION VIEW
def reservation_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        reservation_id = request.POST.get('reservation_id')
        reservation = (
            get_object_or_404(Guests, pk=reservation_id)
            if action == 'update_reservation'
            else Guests()
        )

        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        id_no = request.POST.get('id_no', '').strip()
        county = request.POST.get('county_of_origin', '').strip()
        country = request.POST.get('country', '').strip()
        check_in_date = parse_date(request.POST.get('check_in_date', ''))
        check_out_date = parse_date(request.POST.get('check_out_date', ''))
        room_id = request.POST.get('room')

        if not all((full_name, email, phone_number, id_no, county, country)):
            messages.error(request, 'Complete all guest and reservation fields.')
        elif len(full_name) > 50 or len(phone_number) > 15 or len(id_no) > 12:
            messages.error(request, 'One or more guest details exceed the allowed length.')
        elif not check_in_date or not check_out_date or check_out_date <= check_in_date:
            messages.error(request, 'Choose valid dates and ensure check-out is after check-in.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, 'Enter a valid guest email address.')
            else:
                if Guests.objects.filter(email__iexact=email).exclude(pk=reservation.pk).exists():
                    messages.error(request, 'A reservation already exists for that email address.')
                else:
                    room = get_object_or_404(Rooms, pk=room_id) if room_id else None
                    overlapping = Guests.objects.filter(
                        room=room,
                        check_in_date__lt=check_out_date,
                        check_out_date__gt=check_in_date,
                    ).exclude(pk=reservation.pk)
                    if room and overlapping.exists():
                        messages.error(request, 'That room is already reserved for part of those dates.')
                    else:
                        reservation.full_name = full_name
                        reservation.email = email
                        reservation.phone_number = phone_number
                        reservation.Id_no = id_no
                        reservation.county_of_origin = county
                        reservation.country = country
                        reservation.check_in_date = check_in_date
                        reservation.check_out_date = check_out_date
                        reservation.room = room
                        reservation.save()
                        messages.success(request, 'Reservation saved.')
                        return redirect('admin_portal:reservations')

        return redirect('admin_portal:reservations')

    today = timezone.localdate()
    reservations = Guests.objects.select_related('room').order_by('-check_in_date', '-pk')
    reservation_rows = []
    for reservation in reservations:
        if reservation.check_out_date <= today:
            status, status_class = 'Checked out', 'neutral'
            filter_status = 'checked-out'
        elif reservation.check_in_date <= today:
            status, status_class = 'In house', ''
            filter_status = 'in-house'
        else:
            status, status_class = 'Upcoming', 'pending'
            filter_status = 'upcoming'
        reservation_rows.append({
            'reservation': reservation,
            'status': status,
            'status_class': status_class,
            'filter_status': filter_status,
        })

    return render(request, 'admin_portal/reservations.html', {
        'reservations': reservation_rows,
        'rooms': Rooms.objects.order_by('room_number'),
        'room_types': Rooms.objects.order_by().values_list(
            'room_type', flat=True
        ).distinct(),
        'today': today,
        'total_reservations': Guests.objects.count(),
        'arrivals_today': Guests.objects.filter(check_in_date=today).count(),
        'in_house': Guests.objects.filter(
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).count(),
        'upcoming': Guests.objects.filter(check_in_date__gt=today).count(),
        'checked_out': Guests.objects.filter(check_out_date__lte=today).count(),
    })


def room_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'bulk_availability':
            raw_room_ids = request.POST.getlist('room_ids')
            availability = request.POST.get('bulk_availability')
            try:
                room_ids = {int(room_id) for room_id in raw_room_ids}
            except ValueError:
                messages.error(request, 'Choose valid rooms for the bulk update.')
                return redirect('admin_portal:rooms')

            if not room_ids or availability not in {'available', 'unavailable'}:
                messages.error(request, 'Select rooms and choose an availability status.')
                return redirect('admin_portal:rooms')

            existing_room_ids = set(
                Rooms.objects.filter(pk__in=room_ids).values_list('pk', flat=True)
            )
            if existing_room_ids != room_ids:
                messages.error(request, 'One or more selected rooms no longer exist.')
                return redirect('admin_portal:rooms')

            updated_count = Rooms.objects.filter(pk__in=room_ids).update(
                is_available=availability == 'available'
            )
            messages.success(
                request,
                f'{updated_count} room{"s" if updated_count != 1 else ""} marked {availability}.',
            )
            return redirect('admin_portal:rooms')

        if action == 'delete_room':
            room = get_object_or_404(Rooms, pk=request.POST.get('room_id'))
            room.delete()
            messages.success(request, 'Room removed. Any linked reservations are now unassigned.')
            return redirect('admin_portal:rooms')

        if action in ('create_room', 'update_room'):
            room_id = request.POST.get('room_id')
            room = (
                get_object_or_404(Rooms, pk=room_id)
                if action == 'update_room'
                else Rooms()
            )
            room_number = request.POST.get('room_number', '').strip()
            room_type = request.POST.get('room_type', '').strip()
            price_text = request.POST.get('price', '').strip()

            try:
                price = Decimal(price_text)
            except (ValueError, InvalidOperation):
                messages.error(request, 'Enter a valid room number and nightly rate.')
            else:
                duplicate_number = Rooms.objects.filter(
                    room_number=room_number
                ).exclude(pk=room.pk).exists()
                if not room_number or len(room_number) > 12 or duplicate_number:
                    messages.error(
                        request,
                        'Room numbers must be 1 to 12 characters and unique.',
                    )
                elif not room_type or len(room_type) > 50:
                    messages.error(request, 'Enter a room type of 1–50 characters.')
                elif price <= 0:
                    messages.error(request, 'The nightly rate must be greater than zero.')
                else:
                    uploaded_images = request.FILES.getlist('room_images')
                    try:
                        uploaded_images = [
                            forms.ImageField().clean(image)
                            for image in uploaded_images
                        ]
                    except ValidationError:
                        messages.error(request, 'Upload valid image files only.')
                    else:
                        room.room_number = room_number
                        room.room_type = room_type
                        room.price = price
                        room.is_available = request.POST.get('is_available') == 'on'
                        room.save()
                        for position, uploaded_image in enumerate(
                            uploaded_images,
                            start=room.images.count(),
                        ):
                            RoomImage.objects.create(
                                room=room,
                                image=uploaded_image,
                                position=position,
                            )
                        messages.success(request, 'Room saved.')
                        return redirect('admin_portal:rooms')

            return redirect('admin_portal:rooms')

    rooms = Rooms.objects.annotate(
        reservation_count=Count('reservations', distinct=True),
        room_revenue=Sum(
            'reservations__payments__amount',
            filter=Q(reservations__payments__category='room'),
        ),
    ).order_by('room_number')
    total_room_revenue = Payments.objects.filter(category='room').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    unassigned_room_revenue = Payments.objects.filter(
        category='room',
        guest__room__isnull=True,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    room_categories = list(Rooms.objects.values('room_type').annotate(
        room_count=Count('pk')
    ).order_by('-room_count', 'room_type'))
    category_colors = ['#b9344a', '#8c519a', '#246b4a', '#d781dc', '#d69a36']
    category_total = sum(category['room_count'] for category in room_categories)
    gradient_segments = []
    current_percent = 0
    for index, category in enumerate(room_categories):
        category['color'] = category_colors[index % len(category_colors)]
        next_percent = current_percent + (
            category['room_count'] / category_total * 100
            if category_total else 0
        )
        gradient_segments.append(
            f'{category["color"]} {current_percent:.2f}% {next_percent:.2f}%'
        )
        current_percent = next_percent
    category_gradient = (
        f'conic-gradient({", ".join(gradient_segments)})'
        if gradient_segments else '#eeeaf0'
    )

    return render(request, 'admin_portal/rooms.html', {
        'rooms': rooms,
        'total_rooms': Rooms.objects.count(),
        'available_rooms': Rooms.objects.filter(is_available=True).count(),
        'unavailable_rooms': Rooms.objects.filter(is_available=False).count(),
        'total_room_revenue': total_room_revenue,
        'unassigned_room_revenue': unassigned_room_revenue,
        'room_reservation_count': Guests.objects.filter(room__isnull=False).count(),
        'average_nightly_rate': Rooms.objects.aggregate(
            average=Avg('price')
        )['average'] or Decimal('0.00'),
        'room_categories': room_categories,
        'category_gradient': category_gradient,
        'availability_board': rooms.order_by('is_available', 'room_number')[:4],
    })


def team_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        # DELETING STAFF
        if action == 'delete_staff':
            staff_member = get_object_or_404(Users, pk=request.POST.get('staff_id'))
            staff_member.delete()
            messages.success(request, 'Staff profile removed.')
            return redirect('admin_portal:staff')


        if action in ('create_staff', 'update_staff'):
            staff_id = request.POST.get('staff_id')
            staff_member = (
                get_object_or_404(Users, pk=staff_id)
                if action == 'update_staff'
                else Users()
            )
            fullname = request.POST.get('fullname', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            role = request.POST.get('role', '').strip()
            password = request.POST.get('password', '')

            if not all((fullname, username, email, phone, role)):
                messages.error(request, 'Complete all staff profile fields.')
            # elif len(fullname) > 100 or len(username) > 100 or len(phone) > 10 or len(role) > 100:
            #     messages.error(request, 'One or more staff details exceed the allowed length.')
            
            
            # VALIDATION OF USERNAME AND PASSWORD LENGTH
            elif Users.objects.filter(username__iexact=username).exclude(pk=staff_member.pk).exists():
                messages.error(request, 'That username is already in use.')
            else:
                try:
                    validate_email(email)
                except ValidationError:
                    messages.error(request, 'Enter a valid staff email address.')
                else:
                    if action == 'create_staff' and len(password) < 8:
                        messages.error(request, 'Set an initial password of at least 8 characters.')
                    elif password and len(password) < 8:
                        messages.error(request, 'A new password must be at least 8 characters.')
                    else:
                        staff_member.fullname = fullname
                        staff_member.username = username
                        staff_member.email = email
                        staff_member.phone = phone
                        staff_member.role = role
                        if password:
                            staff_member.password = make_password(password)
                        elif action == 'create_staff':
                            staff_member.password = make_password(None)
                        staff_member.save()
                        messages.success(request, 'Staff profile saved.')
                        return redirect('admin_portal:staff')

            return redirect('admin_portal:staff')

    staff_members = Users.objects.order_by('fullname', 'username')
    roles_count = Users.objects.values('role').distinct().count()
    return render(request, 'admin_portal/staff.html', {
        'staff_members': staff_members,
        'total_staff': Users.objects.count(),
        'roles_count': roles_count,
        'staff_with_email': Users.objects.exclude(email='').count(),
        'staff_with_phone': Users.objects.exclude(phone='').count(),
    })


def revenue_management(request):
    start_text = request.GET.get('start_date', '')
    end_text = request.GET.get('end_date', '')
    start_date = parse_date(start_text) if start_text else None
    end_date = parse_date(end_text) if end_text else None

    if start_text and not start_date:
        messages.error(request, 'Start date must be a valid date.')
    if end_text and not end_date:
        messages.error(request, 'End date must be a valid date.')
    if start_date and end_date and start_date > end_date:
        messages.error(request, 'Start date must be on or before the end date.')
        start_date = end_date = None

    payments = Payments.objects.select_related('guest', 'guest__room').order_by('-payment_date')
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)

    totals = payments.aggregate(
        total=Sum('amount'),
        rooms=Sum('amount', filter=Q(category='room')),
        food=Sum('amount', filter=Q(category='food')),
        other=Sum('amount', filter=Q(category='other')),
    )
    return render(request, 'admin_portal/revenue.html', {
        'payments': payments,
        'total_revenue': totals['total'] or Decimal('0.00'),
        'room_revenue': totals['rooms'] or Decimal('0.00'),
        'food_revenue': totals['food'] or Decimal('0.00'),
        'other_revenue': totals['other'] or Decimal('0.00'),
        'payment_count': payments.count(),
        'start_date': start_date,
        'end_date': end_date,
        'start_date_value': start_text,
        'end_date_value': end_text,
    })




# CONTACTS VIEWS
def contacts(request):
    if request.method == "POST":
        if request.content_type != "application/json":
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": ["Send contact details as JSON."]},
                },
                status=415,
            )

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": ["The contact details are not valid JSON."]},
                },
                status=400,
            )

        if not isinstance(payload, dict):
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"form": ["The contact details must be a JSON object."]},
                },
                status=400,
            )

        fields = (
            "full_name",
            "email",
            "phone_number",
            "inquery_type",
            "subject",
            "message",
        )
        values = {}
        errors = {}
        for field in fields:
            value = payload.get(field)
            if not isinstance(value, str):
                errors[field] = ["This field is required."]
                continue
            value = value.strip()
            if field in {"full_name", "subject"}:
                value = " ".join(value.split())
            elif field == "email":
                value = value.lower()
            elif field == "phone_number":
                value = re.sub(r"[\s().-]", "", value)
            values[field] = value
            if not value:
                errors[field] = ["This field is required."]

        phone_number = values.get("phone_number", "")
        if phone_number and (
            len(phone_number) > 15
            or not re.fullmatch(r"\+?[0-9]{7,15}", phone_number)
        ):
            errors["phone_number"] = ["Enter a valid phone number."]

        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        if Contacts.objects.filter(email__iexact=values["email"]).exists():
            return JsonResponse(
                {
                    "success": False,
                    "errors": {"email": ["A message already uses this email address."]},
                },
                status=400,
            )

        contact = Contacts(**values)
        try:
            contact.full_clean()
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                errors = {
                    field: [str(message) for message in field_messages]
                    for field, field_messages in exc.message_dict.items()
                }
            else:
                errors = {"form": [str(message) for message in exc.messages]}
            return JsonResponse({"success": False, "errors": errors}, status=400)

        contact.save()
        return JsonResponse(
            {
                "success": True,
                "message": "Your message has been received.",
                "contact_id": contact.pk,
            },
            status=201,
        )

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])

    return render(request, "contacts.html")