from django.shortcuts import redirect, render


def staff_login(request):
    return redirect('admin_portal:login')


def staff_dashboard(request):
    return render(request, 'staff_portal/overview.html')


def staff_reservations(request):
    return render(request, 'staff_portal/reservations.html')


def staff_rooms(request):
    return render(request, 'staff_portal/rooms.html')


def staff_contacts(request):
    return render(request, 'staff_portal/contacts.html')
