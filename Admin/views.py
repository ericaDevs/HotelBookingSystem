from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from Billing.models import Payments
from Properties.models import Rooms
from Reservations.models import Guests
from Staff.models import Users

import JsonResponse


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


# API END-POINT VIEW
def api_endpoint(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        role = request.POST.get("role", "").strip().casefold()
        password = request.POST.get("password", "")
        
        
        if not username or not role or not password:
            messages.error(request, "Enter your username, role, and password.")
        else:
            user = Users.objects.filter(username__iexact=username).first()
            admin_roles = {"admin", "administrator"}
            is_admin_user = bool(
                user and user.role.strip().casefold() in admin_roles
            )
        
        # API RESPONSE
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if (
                user
                and check_password(password, user.password)
                and ((role == "admin") == is_admin_user)
            ):
                response_data = {
                    'success': True,
                    'message': f"Welcome back, {user.fullname}!",
                    'redirect_url': '/admin/overview/' if role == "admin" else '/staff/dashboard/',
                }
            else:
                response_data = {
                    'success': False,
                    'message': "Invalid credentials!",
                }
            return JsonResponse(response_data)

    return render(request, 'auth/login.html')




def overview(request):
    return render(request, 'admin_portal/overview.html')



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
        elif reservation.check_in_date <= today:
            status, status_class = 'In house', ''
        else:
            status, status_class = 'Upcoming', 'pending'
        reservation_rows.append({
            'reservation': reservation,
            'status': status,
            'status_class': status_class,
        })

    return render(request, 'admin_portal/reservations.html', {
        'reservations': reservation_rows,
        'rooms': Rooms.objects.order_by('room_number'),
        'today': today,
        'total_reservations': Guests.objects.count(),
        'arrivals_today': Guests.objects.filter(check_in_date=today).count(),
        'in_house': Guests.objects.filter(
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).count(),
        'upcoming': Guests.objects.filter(check_in_date__gt=today).count(),
    })


def room_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
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
                parsed_number = int(room_number)
                price = Decimal(price_text)
            except (ValueError, InvalidOperation):
                messages.error(request, 'Enter a valid room number and nightly rate.')
            else:
                duplicate_number = Rooms.objects.filter(
                    room_number=parsed_number
                ).exclude(pk=room.pk).exists()
                if parsed_number <= 0 or duplicate_number:
                    messages.error(request, 'Room numbers must be positive and unique.')
                elif not room_type or len(room_type) > 50:
                    messages.error(request, 'Enter a room type of 1–50 characters.')
                elif price <= 0:
                    messages.error(request, 'The nightly rate must be greater than zero.')
                else:
                    room.room_number = parsed_number
                    room.room_type = room_type
                    room.price = price
                    room.is_available = request.POST.get('is_available') == 'on'
                    room.save()
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

    return render(request, 'admin_portal/rooms.html', {
        'rooms': rooms,
        'total_rooms': Rooms.objects.count(),
        'available_rooms': Rooms.objects.filter(is_available=True).count(),
        'unavailable_rooms': Rooms.objects.filter(is_available=False).count(),
        'total_room_revenue': total_room_revenue,
        'unassigned_room_revenue': unassigned_room_revenue,
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
